from marshmallow import Schema, fields, validates, validates_schema, ValidationError as MarshmallowValidationError
from backend.utils.error_handler import ValidationError
import bleach
import re

def sanitize_html(value):
    if value and isinstance(value, str):
        return bleach.clean(value, tags=[], strip=True)
    return value

def sanitize_input(data):
    if isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    elif isinstance(data, str):
        return sanitize_html(data)
    return data

class LoginSchema(Schema):
    username = fields.Str(required=True, validate=lambda x: len(x) >= 3)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 6)

class ChangePasswordSchema(Schema):
    current_password = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=lambda x: len(x) >= 8)
    
    @validates('new_password')
    def validate_password_strength(self, value):
        if not re.search(r'[A-Z]', value):
            raise MarshmallowValidationError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', value):
            raise MarshmallowValidationError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', value):
            raise MarshmallowValidationError("Password must contain at least one digit")

class DepartmentSchema(Schema):
    code = fields.Str(required=True, validate=lambda x: len(x) >= 2)
    name = fields.Str(required=True, validate=lambda x: len(x) >= 3)
    description = fields.Str(allow_none=True)
    manager_id = fields.Int(allow_none=True)
    department_type = fields.Str(required=True, validate=lambda x: x in [
        'branding', 'planning', 'quality', 'maintenance', 'finance', 'warehouse', 'other'
    ])
    daily_target = fields.Decimal(allow_none=True)
    weekly_target = fields.Decimal(allow_none=True)
    monthly_target = fields.Decimal(allow_none=True)
    capacity_target = fields.Decimal(allow_none=True)
    config = fields.Dict(allow_none=True)
    is_active = fields.Bool(missing=True)

class EmployeeSchema(Schema):
    employee_number = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    first_name = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    last_name = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    email = fields.Email(allow_none=True)
    phone = fields.Str(allow_none=True)
    department_id = fields.Int(allow_none=True)
    position = fields.Str(allow_none=True)
    employee_type = fields.Str(required=True, validate=lambda x: x in [
        'operator', 'supervisor', 'coordinator', 'manager', 'admin', 
        'applique_cutter', 'packer', 'technician', 'planner', 'qc'
    ])
    is_active = fields.Bool(missing=True)

class MachineSchema(Schema):
    machine_number = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    machine_name = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    department_id = fields.Int(required=True)
    machine_type = fields.Str(allow_none=True)
    manufacturer = fields.Str(allow_none=True)
    model = fields.Str(allow_none=True)
    serial_number = fields.Str(allow_none=True)
    purchase_date = fields.Date(allow_none=True)
    status = fields.Str(missing='available', validate=lambda x: x in [
        'available', 'in_use', 'maintenance', 'broken', 'retired'
    ])
    config = fields.Dict(allow_none=True)
    is_active = fields.Bool(missing=True)

class ProductSchema(Schema):
    product_code = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    product_name = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    description = fields.Str(allow_none=True)
    category = fields.Str(allow_none=True)
    specifications = fields.Dict(allow_none=True)
    is_active = fields.Bool(missing=True)

class OrderSchema(Schema):
    order_number = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    sales_order_number = fields.Str(allow_none=True)
    customer_name = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    product_id = fields.Int(allow_none=True)
    quantity = fields.Int(required=True, validate=lambda x: x > 0)
    order_value = fields.Decimal(allow_none=True)
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)
    priority = fields.Str(missing='normal', validate=lambda x: x in [
        'low', 'normal', 'high', 'urgent'
    ])
    status = fields.Str(missing='unscheduled', validate=lambda x: x in [
        'unscheduled', 'scheduled', 'in_progress', 'completed', 'on_hold', 'cancelled'
    ])
    hold_reason = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)
    config = fields.Dict(allow_none=True)
    
    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise MarshmallowValidationError("Start date cannot be after end date")

class ReplacementTicketSchema(Schema):
    order_id = fields.Int(required=True)
    product_id = fields.Int(allow_none=True)
    quantity_rejected = fields.Int(required=True, validate=lambda x: x > 0)
    department_id = fields.Int(required=True)
    stage_id = fields.Int(allow_none=True)
    rejection_reason = fields.Str(required=True, validate=lambda x: len(x) >= 5)
    rejection_type = fields.Str(required=True, validate=lambda x: x in [
        'material', 'workmanship', 'machine', 'design', 'other'
    ])
    notes = fields.Str(allow_none=True)
    config = fields.Dict(allow_none=True)

class CustomerReturnSchema(Schema):
    order_id = fields.Int(required=True)
    product_id = fields.Int(allow_none=True)
    quantity_returned = fields.Int(required=True, validate=lambda x: x > 0)
    return_reason = fields.Str(required=True, validate=lambda x: len(x) >= 5)
    customer_complaint = fields.Str(allow_none=True)
    return_date = fields.Date(required=True)
    return_type = fields.Str(required=True, validate=lambda x: x in [
        'defect', 'wrong_item', 'damage', 'other'
    ])
    notes = fields.Str(allow_none=True)
    config = fields.Dict(allow_none=True)

class SOPTicketSchema(Schema):
    sop_reference = fields.Str(required=True, validate=lambda x: len(x) >= 1)
    failure_description = fields.Str(required=True, validate=lambda x: len(x) >= 10)
    impact_description = fields.Str(allow_none=True)
    charging_department_id = fields.Int(required=True)
    charged_department_id = fields.Int(required=True)
    notes = fields.Str(allow_none=True)
    config = fields.Dict(allow_none=True)
    
    @validates_schema
    def validate_departments(self, data, **kwargs):
        if data.get('charging_department_id') == data.get('charged_department_id'):
            raise MarshmallowValidationError("A department cannot charge itself")

class MaintenanceTicketSchema(Schema):
    machine_id = fields.Int(required=True)
    department_id = fields.Int(required=True)
    issue_description = fields.Str(required=True, validate=lambda x: len(x) >= 10)
    severity = fields.Str(missing='medium', validate=lambda x: x in [
        'low', 'medium', 'high', 'critical'
    ])
    notes = fields.Str(allow_none=True)
    config = fields.Dict(allow_none=True)

def validate_schema(schema_class, data):
    schema = schema_class()
    try:
        sanitized_data = sanitize_input(data)
        validated_data = schema.load(sanitized_data)
        return validated_data
    except MarshmallowValidationError as e:
        raise ValidationError(str(e.messages), payload={'validation_errors': e.messages})
