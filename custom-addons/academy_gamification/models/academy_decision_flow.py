from odoo import _, api, fields, models
import base64


ECOMMERCE_CHECKLIST = {
    "required": [
        "Ventas",
        "Contactos",
        "Website",
        "eCommerce",
        "Inventario",
        "Facturacion",
    ],
    "recommended": [
        "CRM",
        "Email Marketing",
        "Marketing Automation",
        "Live Chat",
        "WhatsApp (modulo externo)",
    ],
    "advanced": [
        "Suscripciones",
        "Helpdesk",
        "Programa de fidelizacion",
        "Conectores Amazon",
        "Conectores Shopify",
    ],
}

HOSPITALITY_CHECKLIST = {
    "required": [
        "Contactos",
        "Ventas",
        "Compras",
        "Inventario",
        "Facturacion",
        "Punto de Venta (POS)",
    ],
    "recommended": [
        "CRM",
        "Marketing Email",
        "Programa de Fidelizacion",
        "Eventos",
    ],
    "advanced": [
        "Reservas",
        "Kitchen Display",
        "Integracion Delivery",
        "WhatsApp IA",
        "Automatizaciones n8n",
    ],
}


class AcademyDecisionFlow(models.Model):
    _name = "academy.decision.flow"
    _description = "Interactive Decision Flow"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    description = fields.Text()
    points_reward = fields.Integer(default=250)
    level1_ecommerce_channel_id = fields.Many2one("slide.channel", string="Level 1 Ecommerce Channel")
    level1_hospitality_channel_id = fields.Many2one("slide.channel", string="Level 1 Hospitality Channel")
    question_ids = fields.One2many("academy.decision.question", "flow_id")

    _sql_constraints = [
        ("academy_decision_flow_code_unique", "unique(code)", "Flow code must be unique."),
    ]

    def _get_start_question(self):
        self.ensure_one()
        question = self.question_ids.filtered("is_start")[:1]
        if question:
            return question
        return self.question_ids.sorted(key=lambda q: (q.sequence, q.id))[:1]


class AcademyDecisionQuestion(models.Model):
    _name = "academy.decision.question"
    _description = "Interactive Decision Question"
    _order = "sequence, id"

    flow_id = fields.Many2one("academy.decision.flow", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    title = fields.Char(required=True)
    help_text = fields.Text()
    is_start = fields.Boolean(default=False)
    option_ids = fields.One2many("academy.decision.option", "question_id")


class AcademyDecisionOption(models.Model):
    _name = "academy.decision.option"
    _description = "Interactive Decision Option"
    _order = "sequence, id"

    question_id = fields.Many2one("academy.decision.question", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    label = fields.Char(required=True)
    next_question_id = fields.Many2one("academy.decision.question", string="Next Question")

    score_community = fields.Integer(default=0)
    score_enterprise = fields.Integer(default=0)
    score_ecommerce = fields.Integer(default=0)
    score_hospitality = fields.Integer(default=0)
    score_simple = fields.Integer(default=0)
    score_control = fields.Integer(default=0)


class AcademyDecisionSession(models.Model):
    _name = "academy.decision.session"
    _description = "Interactive Decision Session"
    _order = "create_date desc"

    flow_id = fields.Many2one("academy.decision.flow", required=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one("res.partner", related="user_id.partner_id", store=True)
    state = fields.Selection(
        [
            ("in_progress", "In Progress"),
            ("done", "Done"),
        ],
        default="in_progress",
        required=True,
    )
    current_question_id = fields.Many2one("academy.decision.question")
    answer_ids = fields.One2many("academy.decision.answer", "session_id")

    community_score = fields.Integer(default=0)
    enterprise_score = fields.Integer(default=0)
    ecommerce_score = fields.Integer(default=0)
    hospitality_score = fields.Integer(default=0)
    simple_score = fields.Integer(default=0)
    control_score = fields.Integer(default=0)

    edition_recommendation = fields.Selection(
        [("community", "Community"), ("enterprise", "Enterprise")],
        readonly=True,
    )
    track_recommendation = fields.Selection(
        [("ecommerce", "Ecommerce"), ("hospitality", "Hosteleria")],
        readonly=True,
    )
    architecture_recommendation = fields.Selection(
        [("simple", "Odoo Online / Gestionado"), ("control", "Docker / Azure")],
        readonly=True,
    )
    result_summary = fields.Text(readonly=True)
    completed_at = fields.Datetime(readonly=True)
    report_attachment_id = fields.Many2one("ir.attachment", readonly=True, copy=False)

    def _get_track_checklist(self):
        self.ensure_one()
        if self.track_recommendation == "hospitality":
            return HOSPITALITY_CHECKLIST
        return ECOMMERCE_CHECKLIST

    def _get_contextual_recommendations(self):
        self.ensure_one()
        contextual_items = []

        if self.track_recommendation == "ecommerce":
            contextual_items.append({
                "name": "Inventario",
                "status": "base",
                "reason": _("Base operativo de la ruta Ecommerce para catalogo, stock y fulfillment."),
            })
            if self.architecture_recommendation == "simple":
                contextual_items.append({
                    "name": "Website + eCommerce",
                    "status": "active",
                    "reason": _("Tu prioridad de salida rapida favorece una puesta en marcha sobre el stack web estandar."),
                })
            if self.edition_recommendation == "community":
                contextual_items.append({
                    "name": "Conectores Marketplace",
                    "status": "later",
                    "reason": _("La personalizacion alta sugiere dejar Amazon y Shopify para una fase posterior de integraciones."),
                })
            else:
                contextual_items.append({
                    "name": "CRM + Marketing Automation",
                    "status": "active",
                    "reason": _("La recomendacion Enterprise encaja con una operacion comercial y de captacion mas guiada."),
                })
        else:
            contextual_items.append({
                "name": "Punto de Venta (POS)",
                "status": "base",
                "reason": _("Base operativo de Hosteleria para venta en mostrador o mesa."),
            })
            if self.architecture_recommendation == "control":
                contextual_items.append({
                    "name": "Kitchen Display",
                    "status": "active",
                    "reason": _("Tu perfil tecnico y de control encaja mejor con operativas de cocina mas integradas."),
                })
            else:
                contextual_items.append({
                    "name": "Programa de Fidelizacion",
                    "status": "active",
                    "reason": _("La salida rapida favorece empezar por retencion y recurrencia sobre POS."),
                })
            if self.edition_recommendation == "enterprise":
                contextual_items.append({
                    "name": "Marketing Email",
                    "status": "active",
                    "reason": _("La recomendacion Enterprise favorece automatizar captacion y reactivacion desde una base gestionada."),
                })
            else:
                contextual_items.append({
                    "name": "Automatizaciones n8n",
                    "status": "later",
                    "reason": _("Tu perfil de control tecnico deja margen para automatizaciones avanzadas en una fase posterior."),
                })

        return contextual_items

    def get_result_payload(self):
        self.ensure_one()
        checklist = self._get_track_checklist()
        return {
            "edition_label": dict(self._fields["edition_recommendation"].selection).get(self.edition_recommendation),
            "architecture_label": dict(self._fields["architecture_recommendation"].selection).get(self.architecture_recommendation),
            "track_label": dict(self._fields["track_recommendation"].selection).get(self.track_recommendation),
            "checklist_sections": [
                {"key": "required", "title": _("Obligatorios"), "items": checklist["required"]},
                {"key": "recommended", "title": _("Recomendados"), "items": checklist["recommended"]},
                {"key": "advanced", "title": _("Avanzados"), "items": checklist["advanced"]},
            ],
            "contextual_items": self._get_contextual_recommendations(),
            "answers": [
                {
                    "question": answer.question_id.title,
                    "option": answer.option_id.label,
                }
                for answer in self.answer_ids.sorted(key=lambda item: (item.question_id.sequence, item.id))
            ],
        }

    def action_generate_result_pdf(self):
        self.ensure_one()
        if self.state != "done":
            return False

        report = self.env.ref("academy_gamification.action_report_academy_decision_session")
        pdf_content, _content_type = report._render_qweb_pdf(
            report_ref=report.report_name,
            res_ids=self.ids,
        )
        filename = f"diagnostico_{self.flow_id.code}_{self.id}.pdf"

        attachment_vals = {
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(pdf_content),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/pdf",
        }

        if self.report_attachment_id:
            self.report_attachment_id.sudo().write(attachment_vals)
            attachment = self.report_attachment_id
        else:
            attachment = self.env["ir.attachment"].sudo().create(attachment_vals)
            self.report_attachment_id = attachment.id

        return attachment

    @api.model
    def get_or_create_open_session(self, flow):
        session = self.search([
            ("flow_id", "=", flow.id),
            ("user_id", "=", self.env.user.id),
            ("state", "=", "in_progress"),
        ], limit=1)
        if session:
            return session
        start_question = flow._get_start_question()
        return self.create({
            "flow_id": flow.id,
            "user_id": self.env.user.id,
            "current_question_id": start_question.id if start_question else False,
        })

    @api.model
    def create_new_session(self, flow):
        self.search([
            ("flow_id", "=", flow.id),
            ("user_id", "=", self.env.user.id),
            ("state", "=", "in_progress"),
        ]).unlink()
        start_question = flow._get_start_question()
        return self.create({
            "flow_id": flow.id,
            "user_id": self.env.user.id,
            "current_question_id": start_question.id if start_question else False,
        })

    def action_answer(self, option):
        self.ensure_one()
        if self.state != "in_progress":
            return
        question = self.current_question_id
        if not question or option.question_id != question:
            return

        existing = self.answer_ids.filtered(lambda a: a.question_id == question)[:1]
        values = {
            "session_id": self.id,
            "question_id": question.id,
            "option_id": option.id,
        }
        if existing:
            existing.write(values)
        else:
            self.env["academy.decision.answer"].create(values)

        next_question = option.next_question_id
        if not next_question:
            answered_question_ids = self.answer_ids.mapped("question_id").ids
            next_question = self.flow_id.question_ids.filtered(
                lambda q: q.id not in answered_question_ids
            ).sorted(key=lambda q: (q.sequence, q.id))[:1]

        if next_question:
            self.current_question_id = next_question.id
            return

        self._finalize_session()

    def _finalize_session(self):
        self.ensure_one()
        if self.state == "done":
            return

        scores = {
            "community": 0,
            "enterprise": 0,
            "ecommerce": 0,
            "hospitality": 0,
            "simple": 0,
            "control": 0,
        }
        for answer in self.answer_ids:
            option = answer.option_id
            scores["community"] += option.score_community
            scores["enterprise"] += option.score_enterprise
            scores["ecommerce"] += option.score_ecommerce
            scores["hospitality"] += option.score_hospitality
            scores["simple"] += option.score_simple
            scores["control"] += option.score_control

        edition = "community" if scores["community"] >= scores["enterprise"] else "enterprise"
        track = "ecommerce" if scores["ecommerce"] >= scores["hospitality"] else "hospitality"
        architecture = "simple" if scores["simple"] >= scores["control"] else "control"

        summary = _(
            "Decision complete. Recommended edition: %(edition)s. "
            "Recommended architecture: %(architecture)s. "
            "Recommended path: %(track)s."
        ) % {
            "edition": dict(self._fields["edition_recommendation"].selection).get(edition),
            "architecture": dict(self._fields["architecture_recommendation"].selection).get(architecture),
            "track": dict(self._fields["track_recommendation"].selection).get(track),
        }

        self.write({
            "state": "done",
            "current_question_id": False,
            "community_score": scores["community"],
            "enterprise_score": scores["enterprise"],
            "ecommerce_score": scores["ecommerce"],
            "hospitality_score": scores["hospitality"],
            "simple_score": scores["simple"],
            "control_score": scores["control"],
            "edition_recommendation": edition,
            "track_recommendation": track,
            "architecture_recommendation": architecture,
            "result_summary": summary,
            "completed_at": fields.Datetime.now(),
        })

        self._grant_points()
        self._unlock_recommended_level()
        self.action_generate_result_pdf()

    def _grant_points(self):
        self.ensure_one()
        mission_obj = self.env["academy.gamification.mission"].sudo()
        source_key = f"decision_flow_done:{self.flow_id.id}:{self.user_id.id}"
        mission = mission_obj.search([("source_key", "=", source_key)], limit=1)
        if mission:
            if mission.state != "done":
                mission.write({"state": "done", "completion_date": fields.Date.context_today(self)})
            return

        mission_obj.create({
            "name": f"Completed interactive flow: {self.flow_id.name}",
            "description": "Points granted after completing the interactive decision flow.",
            "user_id": self.user_id.id,
            "points": self.flow_id.points_reward,
            "state": "done",
            "completion_date": fields.Date.context_today(self),
            "source_key": source_key,
        })

    def _unlock_recommended_level(self):
        self.ensure_one()
        if not self.partner_id:
            return

        channel = False
        if self.track_recommendation == "ecommerce":
            channel = self.flow_id.level1_ecommerce_channel_id
        elif self.track_recommendation == "hospitality":
            channel = self.flow_id.level1_hospitality_channel_id

        if not channel:
            return

        membership_obj = self.env["slide.channel.partner"].sudo()
        membership = membership_obj.search([
            ("channel_id", "=", channel.id),
            ("partner_id", "=", self.partner_id.id),
        ], limit=1)
        if membership:
            if membership.member_status == "invited":
                membership.member_status = "joined"
            return

        membership_obj.create({
            "channel_id": channel.id,
            "partner_id": self.partner_id.id,
            "member_status": "joined",
        })


class AcademyDecisionAnswer(models.Model):
    _name = "academy.decision.answer"
    _description = "Interactive Decision Answer"
    _order = "id"

    session_id = fields.Many2one("academy.decision.session", required=True, ondelete="cascade")
    question_id = fields.Many2one("academy.decision.question", required=True)
    option_id = fields.Many2one("academy.decision.option", required=True)
