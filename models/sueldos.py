from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class HR_Sueldos(models.Model):
    _name = 'hr.sueldos'
    _description = 'Pago sueldos'

    name = fields.Char(string='mes', index=True)
    nomina_id = fields.Many2one('hr.nomina', string='Nomina', required=True)
    fecha = fields.Date(string='Fecha', required=True)
    observaciones = fields.Text(string='Observaciones')

class HR_Nomina(models.Model):
    _name = 'hr.nomina'
    _description = 'Nomina'

    mes_pago = fields.One2many('hr.sueldos', 'nomina_id', string='Meses de Pago')

    empleado_id = fields.Many2one('hr.employee', string='Nombre', required=True)
    dias_trabajados = fields.Integer(string='Dias Trabajados', default=30)
    dias_ausentes = fields.Integer(string='Dias Ausentes', default=0)
    licencia = fields.Integer(string='Licencia', default=0)
    comienzo = fields.Date(string='Inicio Licencia')
    permisos = fields.Integer(string='Permisos', default=0)
    prestamo = fields.Integer(string='Prestamo', default=0)
    pension = fields.Integer(string='Pension alimentos', default=0)
    pedido_gas = fields.Integer(string='Pedido Gas', default=0)

    b_cumplimiento = fields.Integer(string='Bono Cumplimiento', default=0)
    b_estudio = fields.Integer(string='Bono Estudio', default=0)
    b_est_trabajador = fields.Integer(string='Bono Estudio Trabajador', default=0)
    b_antiguedad = fields.Integer(string='Bono Antiguedad', default=0)
    b_vacaciones = fields.Integer(string='Bono Vacaciones', default=0)
    b_terreno = fields.Integer(string='Bono Trabajo Terreno', default=0)
    viatico = fields.Integer(string='Viatico', default=0)
    b_dia_trabajo = fields.Integer(string='Bono Dia Trabajador', default=0)
    aguinaldo = fields.Integer(string='Aguinaldo', default=0)
    b_productividad = fields.Integer(string='Bono Productividad', default=0)