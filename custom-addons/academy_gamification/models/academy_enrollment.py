import logging

from odoo import models

_logger = logging.getLogger(__name__)

# Producto vendido -> canal de eLearning en el que inscribir al comprador.
# ACADEMY-FUNDADOR-DIGITAL se mantiene por los pedidos ya existentes; no
# tiene canal propio, asi que solo genera usuario del portal y bienvenida.
COURSE_PRODUCT_CHANNELS = {
    'ACADEMY-ECOMMERCE': 'academy_gamification.channel_academy_ecommerce',
    'ACADEMY-HOSTELERIA': 'academy_gamification.channel_academy_hosteleria',
    'ACADEMY-FUNDADOR-DIGITAL': None,
}


class AcademyPaymentTransaction(models.Model):
    """Hook into payment.transaction to grant course access after Stripe confirms payment."""

    _inherit = 'payment.transaction'

    def _post_process(self):
        """Called by Odoo after a transaction reaches a final state (done/cancel/error)."""
        super()._post_process()
        for tx in self.filtered(lambda t: t.state == 'done'):
            try:
                self._academy_grant_course_access(tx)
            except Exception:
                _logger.exception(
                    'Academy enrollment: failed to process access grant for tx %s',
                    tx.reference,
                )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _academy_grant_course_access(self, tx):
        """Find the linked sale order, check it contains the course product,
        then create a portal user and send the welcome email."""
        orders = self.env['sale.order'].sudo().search([
            ('transaction_ids', 'in', [tx.id]),
        ])
        partner = None
        channel_xmlids = set()
        for order in orders:
            for line in order.order_line:
                code = line.product_id.default_code
                if code in COURSE_PRODUCT_CHANNELS:
                    partner = order.partner_id
                    if COURSE_PRODUCT_CHANNELS[code]:
                        channel_xmlids.add(COURSE_PRODUCT_CHANNELS[code])

        if not partner:
            return  # Not a course purchase – nothing to do.

        self._academy_enroll_in_channels(partner, channel_xmlids)

        user, is_new = self._academy_get_or_create_portal_user(partner)
        if user:
            if is_new:
                # Send Odoo's built-in "set your password" invitation email.
                try:
                    user.with_context(create_user=True).action_reset_password()
                except Exception:
                    _logger.exception(
                        'Academy enrollment: could not send password-reset email to %s',
                        user.login,
                    )
            # Always send the custom course welcome email.
            self._academy_send_welcome_email(user)

    def _academy_enroll_in_channels(self, partner, channel_xmlids):
        """Da de alta al comprador en los canales de eLearning comprados."""
        for xmlid in channel_xmlids:
            channel = self.env.ref(xmlid, raise_if_not_found=False)
            if not channel:
                _logger.warning('Academy enrollment: channel %s not found.', xmlid)
                continue
            try:
                # _action_add_members es idempotente: si ya es miembro, no duplica.
                channel.sudo()._action_add_members(partner)
                _logger.info(
                    'Academy enrollment: %s enrolled in %s.', partner.email, xmlid
                )
            except Exception:
                _logger.exception(
                    'Academy enrollment: could not enroll %s in %s.',
                    partner.email, xmlid,
                )

    def _academy_get_or_create_portal_user(self, partner):
        """Return (user, is_new).  Creates a portal user if none exists."""
        User = self.env['res.users'].sudo()

        # Reuse an existing non-public account (e.g. someone who already had a login).
        existing = User.search(
            [('partner_id', '=', partner.id), ('active', 'in', [True, False])],
            limit=1,
        )
        if existing and not existing._is_public():
            _logger.info(
                'Academy enrollment: user already exists for %s – skipping creation.',
                partner.email,
            )
            return existing, False

        # Create a portal user.  no_reset_password suppresses Odoo's default
        # invitation email so we can send our own branded one instead.
        try:
            portal_group = self.env.ref('base.group_portal')
            user = User.with_context(no_reset_password=True).create({
                'name': partner.name,
                'login': partner.email,
                'email': partner.email,
                'partner_id': partner.id,
                'groups_id': [(4, portal_group.id)],
            })
            _logger.info(
                'Academy enrollment: portal user created for %s (id=%s).',
                partner.email,
                user.id,
            )
            return user, True
        except Exception:
            _logger.exception(
                'Academy enrollment: could not create portal user for partner %s.',
                partner.email,
            )
            return None, False

    def _academy_send_welcome_email(self, user):
        """Send the branded welcome email with course access instructions."""
        template = self.env.ref(
            'academy_gamification.mail_template_academy_course_welcome',
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning('Academy enrollment: welcome email template not found.')
            return
        try:
            template.sudo().send_mail(user.id, force_send=True)
            _logger.info(
                'Academy enrollment: welcome email sent to %s.',
                user.email,
            )
        except Exception:
            _logger.exception(
                'Academy enrollment: failed to send welcome email to %s.',
                user.email,
            )
