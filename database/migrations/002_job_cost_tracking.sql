-- Migration: 002 - Job Cost Tracking
-- Date: 2026-01-20
-- Description: Adds labor and overhead cost tracking to job schedules

USE railway;

-- 1. Add cost tracking columns to job_schedules
ALTER TABLE job_schedules 
ADD COLUMN material_cost DECIMAL(12,2) DEFAULT 0 AFTER actual_quantity,
ADD COLUMN labor_cost DECIMAL(12,2) DEFAULT 0 AFTER material_cost,
ADD COLUMN overhead_cost DECIMAL(12,2) DEFAULT 0 AFTER labor_cost,
ADD COLUMN total_cost DECIMAL(12,2) GENERATED ALWAYS AS (material_cost + labor_cost + overhead_cost) STORED,
ADD COLUMN standard_cost DECIMAL(12,2) DEFAULT 0 AFTER total_cost,
ADD COLUMN cost_variance DECIMAL(12,2) GENERATED ALWAYS AS (total_cost - standard_cost) STORED,
ADD COLUMN actual_hours DECIMAL(10,2) DEFAULT 0 AFTER cost_variance,
ADD COLUMN standard_hours DECIMAL(10,2) DEFAULT 0 AFTER actual_hours,
ADD INDEX idx_cost_tracking (status, completed_at);

-- 2. Create view for job profitability analysis
CREATE OR REPLACE VIEW v_job_profitability AS
SELECT 
    js.id as schedule_id,
    js.order_id,
    o.order_number,
    o.customer_name,
    p.product_name,
    d.name as department_name,
    js.scheduled_date,
    js.scheduled_quantity,
    js.actual_quantity,
    js.material_cost,
    js.labor_cost,
    js.overhead_cost,
    js.total_cost,
    js.standard_cost,
    js.cost_variance,
    js.actual_hours,
    js.standard_hours,
    js.status,
    CASE 
        WHEN js.actual_quantity > 0 THEN js.total_cost / js.actual_quantity
        ELSE 0
    END as cost_per_unit,
    CASE
        WHEN js.actual_hours > 0 THEN js.actual_quantity / js.actual_hours
        ELSE 0
    END as productivity_rate,
    DATE_FORMAT(js.completed_at, '%Y-%m') as month_year
FROM job_schedules js
LEFT JOIN orders o ON js.order_id = o.id
LEFT JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN products p ON oi.product_id = p.id
LEFT JOIN departments d ON js.department_id = d.id
WHERE js.status = 'completed'
ORDER BY js.completed_at DESC;

-- 3. Create view for department cost analysis
CREATE OR REPLACE VIEW v_department_cost_analysis AS
SELECT 
    d.id as department_id,
    d.name as department_name,
    DATE_FORMAT(js.completed_at, '%Y-%m') as month_year,
    COUNT(DISTINCT js.id) as jobs_completed,
    SUM(js.actual_quantity) as total_units_produced,
    SUM(js.material_cost) as total_material_cost,
    SUM(js.labor_cost) as total_labor_cost,
    SUM(js.overhead_cost) as total_overhead_cost,
    SUM(js.total_cost) as total_cost,
    SUM(js.standard_cost) as total_standard_cost,
    SUM(js.cost_variance) as total_cost_variance,
    AVG(js.total_cost / NULLIF(js.actual_quantity, 0)) as avg_cost_per_unit,
    SUM(js.actual_hours) as total_hours_worked
FROM departments d
LEFT JOIN job_schedules js ON d.id = js.department_id
WHERE js.status = 'completed'
GROUP BY d.id, d.name, DATE_FORMAT(js.completed_at, '%Y-%m')
ORDER BY month_year DESC, d.name;

-- 4. Create trigger for automatic cost calculation on job completion
DELIMITER $$

CREATE TRIGGER trg_calculate_job_costs BEFORE UPDATE ON job_schedules
FOR EACH ROW
BEGIN
    DECLARE bom_material_cost DECIMAL(12,2);
    DECLARE product_bom_id INT;
    DECLARE product_item_id INT;
    DECLARE labor_rate DECIMAL(10,2);
    DECLARE overhead_rate DECIMAL(12,2);
    DECLARE emp_position VARCHAR(100);
    
    -- Only calculate if status is being set to completed
    IF NEW.status = 'completed' AND OLD.status != 'completed' AND NEW.total_cost = 0 THEN
        
        -- Get product from order
        SELECT oi.id, oi.product_id INTO product_item_id, @product_id
        FROM order_items oi
        WHERE oi.order_id = NEW.order_id
        LIMIT 1;
        
        IF @product_id IS NOT NULL THEN
            -- 1. Calculate material cost from BOM
            SELECT b.id INTO product_bom_id
            FROM bom b
            WHERE b.product_id = @product_id
            AND b.is_active = TRUE
            ORDER BY b.effective_date DESC
            LIMIT 1;
            
            IF product_bom_id IS NOT NULL THEN
                SELECT SUM(bi.total_cost) INTO bom_material_cost
                FROM bom_items bi
                WHERE bi.bom_id = product_bom_id;
                
                SET NEW.material_cost = (COALESCE(bom_material_cost, 0) * COALESCE(NEW.actual_quantity, 0));
            END IF;
            
            -- 2. Calculate labor cost based on actual hours and employee rate
            IF NEW.assigned_employee_id IS NOT NULL AND NEW.actual_hours > 0 THEN
                SELECT e.position INTO emp_position
                FROM employees e
                WHERE e.id = NEW.assigned_employee_id;
                
                SELECT lcm.hourly_rate INTO labor_rate
                FROM labor_cost_models lcm
                WHERE lcm.department_id = NEW.department_id
                AND lcm.position = COALESCE(emp_position, 'General')
                AND lcm.is_active = TRUE
                AND CURDATE() BETWEEN lcm.effective_from AND COALESCE(lcm.effective_to, '2099-12-31')
                ORDER BY lcm.effective_from DESC
                LIMIT 1;
                
                SET NEW.labor_cost = (COALESCE(labor_rate, 0) * NEW.actual_hours);
            END IF;
            
            -- 3. Calculate overhead cost based on department allocation
            SELECT SUM(
                CASE 
                    WHEN ocm.allocation_method = 'per_unit' THEN ocm.cost_amount * COALESCE(NEW.actual_quantity, 0)
                    WHEN ocm.allocation_method = 'per_hour' THEN ocm.cost_amount * COALESCE(NEW.actual_hours, 0)
                    WHEN ocm.allocation_method = 'percentage' THEN (NEW.material_cost + NEW.labor_cost) * (ocm.cost_amount / 100)
                    ELSE 0
                END
            ) INTO overhead_rate
            FROM overhead_cost_models ocm
            WHERE ocm.department_id = NEW.department_id
            AND ocm.is_active = TRUE
            AND CURDATE() BETWEEN ocm.effective_from AND COALESCE(ocm.effective_to, '2099-12-31');
            
            SET NEW.overhead_cost = COALESCE(overhead_rate, 0);
        END IF;
    END IF;
END$$

DELIMITER ;

-- Rollback script (commented out - save for reference)
-- ALTER TABLE job_schedules 
-- DROP COLUMN material_cost,
-- DROP COLUMN labor_cost,
-- DROP COLUMN overhead_cost,
-- DROP COLUMN total_cost,
-- DROP COLUMN standard_cost,
-- DROP COLUMN cost_variance,
-- DROP COLUMN actual_hours,
-- DROP COLUMN standard_hours;
-- DROP VIEW IF EXISTS v_job_profitability;
-- DROP VIEW IF EXISTS v_department_cost_analysis;
-- DROP TRIGGER IF EXISTS trg_calculate_job_costs;
