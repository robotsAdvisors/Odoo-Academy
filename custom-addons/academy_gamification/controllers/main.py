from odoo import http
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
from werkzeug.exceptions import NotFound
import json
import logging
import re

_logger = logging.getLogger(__name__)


LINKEDIN_POSTS_PARAM = "academy_gamification.linkedin_posts"
DEFAULT_LINKEDIN_POSTS = [
    "https://www.linkedin.com/posts/robotsconsultant_industria40-digitalizaciaejn-ayudasempresas-activity-7480508112672624640-f4kg",
    "https://www.linkedin.com/posts/robotsconsultant_la-ia-en-odoo-no-sustituye-al-comercial-activity-7477985758331674625-Sm6h",
    "https://www.linkedin.com/posts/robotsconsultant_hosteleraeda-restaurantes-cafeteraedas-activity-7477688277169287170-Fz9Q",
    "https://www.linkedin.com/posts/robotsconsultant_y-aqu%C3%AD-est%C3%A1-lo-que-nadie-te-cuenta-esto-activity-7475474603470000128-9BKQ",
]


class AcademyDecisionController(http.Controller):

    def _json_response(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=True)
        headers = [("Content-Type", "application/json")]
        return request.make_response(body, headers=headers, status=status)

    def _normalize_linkedin_url(self, url):
        if not url:
            return None
        clean_url = str(url).strip()
        if not clean_url:
            return None
        clean_url = clean_url.split("?")[0]

        activity_match = re.search(r"activity-(\d+)", clean_url)
        if not activity_match:
            activity_match = re.search(r"urn:li:activity:(\d+)", clean_url)
        if not activity_match:
            return None

        activity_id = activity_match.group(1)
        return {
            "activity_id": activity_id,
            "source_url": clean_url,
            "embed_url": f"https://www.linkedin.com/embed/feed/update/urn:li:activity:{activity_id}",
            "title": f"LinkedIn post {activity_id}",
        }

    def _get_stored_linkedin_posts(self):
        param_obj = request.env["ir.config_parameter"].sudo()
        raw = param_obj.get_param(LINKEDIN_POSTS_PARAM)
        if not raw:
            normalized = [
                self._normalize_linkedin_url(url)
                for url in DEFAULT_LINKEDIN_POSTS
            ]
            normalized = [post for post in normalized if post]
            return normalized

        try:
            data = json.loads(raw)
        except Exception:
            return []

        normalized = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    source = item.get("source_url") or item.get("url") or item.get("embed_url")
                else:
                    source = item
                post = self._normalize_linkedin_url(source)
                if post:
                    normalized.append(post)
        return normalized

    def _can_manage_news_from_session(self):
        user = request.env.user
        if not user or user._is_public():
            return False
        return user.has_group("base.group_system")

    def _save_linkedin_posts(self, posts):
        request.env["ir.config_parameter"].sudo().set_param(
            LINKEDIN_POSTS_PARAM,
            json.dumps(posts, ensure_ascii=True),
        )

    @http.route(["/"], type="http", auth="public", website=True, sitemap=True)
    def website_home_landing(self, **kwargs):
        return request.render("academy_gamification.digitaliza_tu_negocio_landing")

    @http.route([
        "/academy/digitaliza-tu-negocio",
        "/odoo/academy/digitaliza-tu-negocio",
    ], type="http", auth="public", website=True)
    def digitaliza_tu_negocio_landing(self, **kwargs):
        return request.render("academy_gamification.digitaliza_tu_negocio_landing")

    @http.route([
        "/servicios",
        "/our-services",
        "/academy/servicios",
        "/odoo/academy/servicios",
    ], type="http", auth="public", website=True, sitemap=True)
    def servicios_landing(self, **kwargs):
        return request.render("academy_gamification.servicios_landing")

    @http.route([
        "/news",
        "/academy/news",
    ], type="http", auth="public", website=True, sitemap=True)
    def news_landing(self, **kwargs):
        values = {
            "linkedin_posts": self._get_stored_linkedin_posts(),
            "can_manage_news": self._can_manage_news_from_session(),
        }
        return request.render("academy_gamification.news_landing", values)

    @http.route(
        "/api/news/linkedin",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        website=False,
    )
    def api_get_linkedin_news(self, **kwargs):
        posts = self._get_stored_linkedin_posts()
        return self._json_response({"count": len(posts), "posts": posts})

    @http.route(
        "/api/news/linkedin",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def api_set_linkedin_news(self, **kwargs):
        body = request.httprequest.get_json(silent=True) or {}
        if not self._can_manage_news_from_session():
            return self._json_response({"ok": False, "error": "Admin authentication required"}, status=401)

        posts = body.get("posts") if isinstance(body, dict) else None
        if not isinstance(posts, list):
            return self._json_response({"ok": False, "error": "Field 'posts' must be a list"}, status=400)

        normalized = []
        for item in posts:
            url = item.get("url") if isinstance(item, dict) else item
            post = self._normalize_linkedin_url(url)
            if post:
                normalized.append(post)

        if not normalized:
            return self._json_response({"ok": False, "error": "No valid LinkedIn post URLs"}, status=400)

        self._save_linkedin_posts(normalized)

        return self._json_response(
            {
                "ok": True,
                "count": len(normalized),
                "posts": normalized,
            },
            status=200,
        )

    @http.route(
        "/api/news/linkedin/add",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def api_add_linkedin_news(self, **kwargs):
        body = request.httprequest.get_json(silent=True) or {}
        if not self._can_manage_news_from_session():
            return self._json_response({"ok": False, "error": "Admin authentication required"}, status=401)

        url = ""
        if isinstance(body, dict):
            url = body.get("url") or ""
        post = self._normalize_linkedin_url(url)
        if not post:
            return self._json_response({"ok": False, "error": "Invalid LinkedIn URL"}, status=400)

        posts = self._get_stored_linkedin_posts()
        if any(item.get("activity_id") == post.get("activity_id") for item in posts):
            return self._json_response(
                {
                    "ok": True,
                    "message": "Post already exists",
                    "count": len(posts),
                    "posts": posts,
                },
                status=200,
            )

        posts.insert(0, post)
        self._save_linkedin_posts(posts)
        return self._json_response(
            {
                "ok": True,
                "count": len(posts),
                "posts": posts,
            },
            status=200,
        )

    @http.route("/web/academy/fundador-digital", type="http", auth="user")
    def fundador_digital_launcher(self, **kwargs):
        db = request.db or request.session.db
        return request.redirect(f"/academy/fundador-digital?db={db}")

    @http.route([
        "/academy/fundador-digital",
        "/odoo/academy/fundador-digital",
    ], type="http", auth="public", website=True)
    def fundador_digital(self, **kwargs):
        if request.env.user._is_public():
            return request.redirect("/web/login?redirect=/academy/fundador-digital")

        flow = request.env["academy.decision.flow"].sudo().search([
            ("code", "=", "fundador_digital")
        ], limit=1)
        if not flow:
            return request.not_found()

        # Keep the real request user in session ownership checks/creation.
        session_obj = request.env["academy.decision.session"]
        if kwargs.get("new"):
            session = session_obj.create_new_session(flow)
        elif kwargs.get("session_id"):
            session = session_obj.browse(int(kwargs["session_id"]))
            if not session.exists() or session.user_id != request.env.user or session.flow_id != flow:
                session = session_obj.get_or_create_open_session(flow)
        else:
            session = session_obj.get_or_create_open_session(flow)

        if session.user_id != request.env.user:
            return request.redirect("/web")

        values = {
            "flow": flow,
            "session": session,
            "question": session.current_question_id,
            "total_questions": len(flow.question_ids),
            "answered_questions": len(session.answer_ids),
            "result_payload": session.get_result_payload() if session.state == "done" else {},
        }
        return request.render("academy_gamification.fundador_digital_page", values)

    @http.route(
        [
            "/academy/fundador-digital/answer",
            "/odoo/academy/fundador-digital/answer",
        ],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def fundador_digital_answer(self, session_id=None, option_id=None, **kwargs):
        if not session_id or not option_id:
            return request.redirect("/academy/fundador-digital")

        session = request.env["academy.decision.session"].browse(int(session_id))
        option = request.env["academy.decision.option"].browse(int(option_id))

        if not session.exists() or not option.exists() or session.user_id != request.env.user:
            return request.redirect("/academy/fundador-digital")

        session.action_answer(option)
        return request.redirect(f"/academy/fundador-digital?session_id={session.id}")

    @http.route(
        [
            "/academy/fundador-digital/report/<int:session_id>",
            "/odoo/academy/fundador-digital/report/<int:session_id>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def fundador_digital_report(self, session_id, **kwargs):
        session = request.env["academy.decision.session"].browse(session_id)
        if not session.exists() or session.user_id != request.env.user or session.state != "done":
            raise NotFound()

        report = request.env.ref("academy_gamification.action_report_academy_decision_session")
        pdf_content, _content_type = report._render_qweb_pdf(
            report_ref=report.report_name,
            res_ids=[session.id],
        )
        if not pdf_content:
            raise NotFound()

        filename = f"diagnostico_{session.flow_id.code}_{session.id}.pdf"

        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", str(len(pdf_content))),
            ("Content-Disposition", f'attachment; filename="{filename}"'),
        ]
        return request.make_response(pdf_content, headers=headers)

    # ──────────────────────────────────────────────────────────────────
    #  Inscripción + pago directo con Stripe
    # ──────────────────────────────────────────────────────────────────

    @http.route('/academy/inscripcion', type='http', auth='public', website=True, methods=['GET'])
    def academy_inscripcion_form(self, **kwargs):
        """Muestra el formulario de captura de nombre y email antes del pago."""
        return request.render('academy_gamification.academy_inscripcion_form')

    @http.route('/academy/inscripcion', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def academy_inscripcion_submit(self, nombre='', email='', **kwargs):
        """Crea partner + orden de venta y redirige a la página de pago del portal."""
        nombre = (nombre or '').strip()
        email = (email or '').strip().lower()

        error_vals = {'nombre': nombre, 'email': email}

        if not nombre or not email:
            return request.render(
                'academy_gamification.academy_inscripcion_form',
                {**error_vals, 'error': 'Por favor completa todos los campos.'},
            )

        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return request.render(
                'academy_gamification.academy_inscripcion_form',
                {**error_vals, 'error': 'El formato del email no es válido.'},
            )

        env = request.env

        # ── Partner ──────────────────────────────────────────────────
        Partner = env['res.partner'].sudo()
        partner = Partner.search([('email', '=', email)], limit=1)
        if not partner:
            partner = Partner.create({'name': nombre, 'email': email})

        # ── Moneda EUR ───────────────────────────────────────────────
        currency = env['res.currency'].sudo().search([('name', '=', 'EUR')], limit=1)
        if not currency:
            currency = env['res.currency'].sudo().browse(1)

        # ── Producto ─────────────────────────────────────────────────
        product = env['product.product'].sudo().search(
            [('default_code', '=', 'ACADEMY-FUNDADOR-DIGITAL')], limit=1
        )
        if not product:
            _logger.error('Academy checkout: product ACADEMY-FUNDADOR-DIGITAL not found.')
            return request.render(
                'academy_gamification.academy_inscripcion_form',
                {**error_vals, 'error': 'Error interno. Por favor contacta con soporte.'},
            )

        # ── Orden de venta ───────────────────────────────────────────
        order = env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'currency_id': currency.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_uom_qty': 1.0,
                'price_unit': 22.0,
            })],
        })
        order._portal_ensure_token()

        # ── Redirige al portal de la orden para que el usuario pague ─
        # El portal muestra el resumen del pedido con el botón "Pagar"
        # que lanza el formulario de Stripe de Odoo.
        portal_url = f'/my/orders/{order.id}?access_token={order.access_token}'
        return request.redirect(portal_url)

    @http.route('/academy/gracias', type='http', auth='public', website=True)
    def academy_pago_gracias(self, **kwargs):
        """Página de confirmación post-pago (landing opcional)."""
        return request.render('academy_gamification.academy_pago_gracias')
