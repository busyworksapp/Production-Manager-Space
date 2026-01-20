-- Migration: Item-Level Defect Tracking and Cost Impact
-- Date: 2026-01-20
-- Description: Adds support for tracking defects at order item level and calculating cost impact

USE railway;

-- 1. Add order_item_id to replacement_tickets
ALTER TABLE replacement_tickets 
ADD COLUMN order_item_id INT NULL AFTER product_id,
ADD COLUMN cost_impact DECIMAL(12,2) DEFAULT 0 AFTER quantity_rejected,
ADD COLUMN material_cost DECIMAL(12,2) DEFAULT 0 AFTER cost_impact,
ADD COLUMN labor_cost DECIMAL(12,2) DEFAULT 0 AFTER material_cost,
ADD COLUMN total_cost DECIMAL(12,2) GENERATED ALWAYS AS (material_cost + labor_cost) STORED,
ADD FOREIGN KEY (order_item_id) REFERENCES order_items(id) ON DELETE SET NULL,
ADD INDEX idx_order_item (order_item_id);

-- 2. Add order_item_id to customer_returns
ALTER TABLE customer_returns
ADD COLUMN order_item_id INT NULL AFTER product_id,
ADD COLUMN cost_impact DECIMAL(12,2) DEFAULT 0 AFTER quantity_returned,
ADD COLUMN material_cost DECIMAL(12,2) DEFAULT 0 AFTER cost_impact,
ADD COLUMN labor_cost DECIMAL(12,2) DEFAULT 0 AFTER material_cost,
ADD COLUMN total_cost DECIMAL(12,2) GENERATED ALWAYS AS (material_cost + labor_cost) STORED,
ADD FOREIGN KEY (order_item_id) REFERENCES order_items(id) ON DELETE SET NULL,
ADD INDEX idx_order_item (order_item_id);

-- 3. Add notification tracking for no-stock status
CREATE TABLE IF NOT EXISTS defect_notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    replacement_ticket_id INT NOT NULL,
    notification_type ENUM('no_stock_manager', 'no_stock_planning_manager', 'no_stock_hod', 'approval_required', 'approved') NOT NULL,
    recipient_id INT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_status ENUM('pending', 'sent', 'failed') DEFAULT 'sent',
    email_details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (replacement_ticket_id) REFERENCES replacement_tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_ticket (replacement_ticket_id),
    INDEX idx_recipient (recipient_id),
    INDEX idx_type (notification_type),
    INDEX idx_sent (sent_at)
) ENGINE=InnoDB;

-- 4. Create view for cost impact analysis
CREATE OR REPLACE VIEW v_defect_cost_analysis AS
SELECT 
    d.name as department_name,
    COUNT(DISTINCT rt.id) as total_rejects,
    SUM(rt.quantity_rejected) as total_quantity_rejected,
    SUM(rt.material_cost) as total_material_cost,
    SUM(rt.labor_cost) as total_labor_cost,
    SUM(rt.total_cost) as total_cost_impact,
    AVG(rt.material_cost) as avg_material_cost_per_reject,
    DATE_FORMAT(rt.created_at, '%Y-%m') as month_year
FROM replacement_tickets rt
LEFT JOIN departments d ON rt.department_id = d.id
WHERE rt.status IN ('approved', 'replacement_processed')
GROUP BY d.id, d.name, DATE_FORMAT(rt.created_at, '%Y-%m')
ORDER BY rt.created_at DESC;

-- 5. Create view for customer returns cost analysis
CREATE OR REPLACE VIEW v_customer_returns_cost_analysis AS
SELECT 
    p.product_name,
    p.category,
    COUNT(DISTINCT cr.id) as total_returns,
    SUM(cr.quantity_returned) as total_quantity_returned,
    SUM(cr.material_cost) as total_material_cost,
    SUM(cr.labor_cost) as total_labor_cost,
    SUM(cr.total_cost) as total_cost_impact,
    DATE_FORMAT(cr.created_at, '%Y-%m') as month_year
FROM customer_returns cr
LEFT JOIN products p ON cr.product_id = p.id
GROUP BY p.id, p.product_name, p.category, DATE_FORMAT(cr.created_at, '%Y-%m')
ORDER BY cr.created_at DESC;

-- 6. Add indexes for performance optimization
ALTER TABLE replacement_tickets ADD INDEX idx_status_created (status, created_at);
ALTER TABLE customer_returns ADD INDEX idx_return_date (return_date);
ALTER TABLE order_items ADD INDEX idx_order_status (order_id, status);

-- 7. Add trigger to auto-calculate cost impact when BOM exists
DELIMITER $$

CREATE TRIGGER trg_calculate_replacement_cost BEFORE UPDATE ON replacement_tickets
FOR EACH ROW
BEGIN
    DECLARE bom_material_cost DECIMAL(12,2);
    DECLARE product_bom_id INT;
    
    -- Only calculate if status is being approved and cost not already set
    IF NEW.status = 'approved' AND OLD.status = 'pending_approval' AND NEW.material_cost = 0 THEN
        -- Get active BOM for the product
        SELECT b.id INTO product_bom_id
        FROM bom b
        WHERE b.product_id = NEW.product_id
        AND b.is_active = TRUE
        ORDER BY b.effective_date DESC
        LIMIT 1;
        
        IF product_bom_id IS NOT NULL THEN
            -- Calculate material cost from BOM
            SELECT SUM(bi.total_cost) INTO bom_material_cost
            FROM bom_items bi
            WHERE bi.bom_id = product_bom_id;
            
            -- Set material cost based on rejected quantity
            SET NEW.material_cost = (bom_material_cost * NEW.quantity_rejected);
            SET NEW.cost_impact = NEW.material_cost;
        END IF;
    END IF;
END$$

DELIMITER ;

-- Rollback script (commented out - save for reference)
-- ALTER TABLE replacement_tickets DROP FOREIGN KEY replacement_tickets_ibfk_order_item;
-- ALTER TABLE replacement_tickets DROP COLUMN order_item_id, DROP COLUMN cost_impact, DROP COLUMN material_cost, DROP COLUMN labor_cost, DROP COLUMN total_cost;
-- ALTER TABLE customer_returns DROP FOREIGN KEY customer_returns_ibfk_order_item;
-- ALTER TABLE customer_returns DROP COLUMN order_item_id, DROP COLUMN cost_impact, DROP COLUMN material_cost, DROP COLUMN labor_cost, DROP COLUMN total_cost;
-- DROP TABLE IF EXISTS defect_notifications;
-- DROP VIEW IF EXISTS v_defect_cost_analysis;
-- DROP VIEW IF EXISTS v_customer_returns_cost_analysis;
-- DROP TRIGGER IF EXISTS trg_calculate_replacement_cost;
