from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class HR_Sueldos(models.Model):
    _name = 'hr.sueldos'
    _description = 'Pago sueldos'

    name = fields.Char(string='mes', index=True)
    nombre = fields.Many2one('hr.employee', string='Empleado', required=True) 