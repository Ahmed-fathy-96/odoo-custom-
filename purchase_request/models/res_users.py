from odoo.exceptions import Warning
from odoo import api, exceptions, fields, models
from collections import defaultdict


class ResUsersExt(models.Model):
    _inherit = 'res.users'

    age = fields.Integer()

    @api.model
    def signup(self, values, token=None):
        """ signup a user, to either:
            - create a new user (no token), or
            - create a user for a partner (with token, but no user for partner), or
            - change the password of a user (with token, and existing user).
            :param values: a dictionary with field values that are written on user
            :param token: signup token (optional)
            :return: (dbname, login, password) for the signed up user
        """
        # if token:
        #     # signup with a token: find the corresponding partner id
        #     partner = self.env['res.partner']._signup_retrieve_partner(token, check_validity=True, raise_exception=True)
        #     # invalidate signup token
        #     partner.write({'signup_token': False, 'signup_type': False, 'signup_expiration': False, 'age': values.get('age') })
        #     partner.write({'age' :  values.get('age')})
        #     partner_user = partner.user_ids and partner.user_ids[0] or False
        #
        #     # avoid overwriting existing (presumably correct) values with geolocation data
        #     if partner.country_id or partner.zip or partner.city:
        #         values.pop('city', None)
        #         values.pop('country_id', None)
        #     if partner.lang:
        #         values.pop('lang', None)
        #
        #     if partner_user:
        #         # user exists, modify it according to values
        #         values.pop('login', None)
        #         values.pop('name', None)
        #         partner_user.write(values)
        #         if not partner_user.login_date:
        #             partner_user._notify_inviter()
        #         return (self.env.cr.dbname, partner_user.login, values.get('password'))
        #     else:
        #         # user does not exist: sign up invited user
        #         values.update({
        #             'name': partner.name,
        #             'partner_id': partner.id,
        #             'email': values.get('email') or values.get('login'),
        #         })
        #         if partner.company_id:
        #             values['company_id'] = partner.company_id.id
        #             values['company_ids'] = [(6, 0, [partner.company_id.id])]
        #         partner_user = self._signup_create_user(values)
        #         partner_user._notify_inviter()
        # else:
        #     # no token, sign up an external user
        #     values['email'] = values.get('email') or values.get('login')
        #     self._signup_create_user(values)
        #
        # return (self.env.cr.dbname, values.get('login'), values.get('password'))
        #
        res = super(ResUsersExt, self).signup(values)
        print(".......run......")
        return res


class ResPartnerExt(models.Model):
    _inherit = 'res.partner'

    age = fields.Integer()

    def signup_get_auth_param(self):
        """ Get a signup token related to the partner if signup is enabled.
            If the partner already has a user, get the login parameter.
        """
        if not self.env.user.has_group('base.group_user') and not self.env.is_admin():
            raise exceptions.AccessDenied()

        res = defaultdict(dict)

        allow_signup = self.env['res.users']._get_signup_invitation_scope() == 'b2c'
        for partner in self:
            partner = partner.sudo()
            if allow_signup and not partner.user_ids:
                partner.signup_prepare()
                res[partner.id]['auth_signup_token'] = partner.signup_token
            elif partner.user_ids:
                res[partner.id]['auth_login'] = partner.user_ids[0].login
        return res

    # @api.model
    # def create(self,vals_list):
    #     print(1/0)
    #     return super(ResPartnerExt, self).create(vals_list)
    # def _age_compute(self):
    #     for rec in self:
    #         for user in rec.user_ids[0]:
    #             if user:
    #                 print("......user name.....",  user.name )
    #                 rec.age = user.age
    #         else:
    #             rec.age = 50000
