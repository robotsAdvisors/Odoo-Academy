from odoo import api, fields, models


class AcademyMission(models.Model):
    _name = "academy.gamification.mission"
    _description = "Gamification Mission"
    _order = "create_date desc"
    _sql_constraints = [
        ("academy_gamification_mission_source_key_uniq", "unique(source_key)", "Mission source key must be unique."),
    ]

    name = fields.Char(required=True)
    description = fields.Text()
    user_id = fields.Many2one("res.users", string="Assigned To", default=lambda self: self.env.user, required=True)
    points = fields.Integer(default=10)
    source_key = fields.Char(index=True, copy=False)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done")
        ],
        default="draft",
        required=True,
    )
    completion_date = fields.Date(readonly=True)

    def action_mark_done(self):
        for mission in self.filtered(lambda m: m.state != "done"):
            mission.write({
                "state": "done",
                "completion_date": fields.Date.context_today(self),
            })


class ResUsers(models.Model):
    _inherit = "res.users"

    gamification_points = fields.Integer(
        string="Gamification Points",
        compute="_compute_gamification_stats",
        store=False,
    )
    gamification_level = fields.Selection(
        [
            ("bronze", "Bronze"),
            ("silver", "Silver"),
            ("gold", "Gold"),
            ("platinum", "Platinum"),
            ("diamond", "Diamond"),
        ],
        string="Gamification Level",
        compute="_compute_gamification_stats",
        store=False,
    )
    gamification_rank = fields.Integer(
        string="Gamification Rank",
        compute="_compute_gamification_stats",
        store=False,
    )

    def _get_gamification_level(self, points):
        if points >= 2000:
            return "diamond"
        if points >= 1200:
            return "platinum"
        if points >= 700:
            return "gold"
        if points >= 300:
            return "silver"
        return "bronze"

    @api.depends("name")
    def _compute_gamification_stats(self):
        users = self.env["res.users"].sudo().search([
            ("active", "=", True),
            ("share", "=", False),
        ])

        grouped = self.env["academy.gamification.mission"].sudo().read_group(
            [("state", "=", "done"), ("user_id", "in", users.ids)],
            ["user_id", "points:sum"],
            ["user_id"],
        )
        by_user = {row["user_id"][0]: row["points"] for row in grouped if row.get("user_id")}

        ranked_users = sorted(
            users,
            key=lambda u: (-int(by_user.get(u.id, 0)), (u.name or ""), u.id),
        )

        rank_by_user = {}
        current_rank = 0
        previous_points = None
        for index, ranked_user in enumerate(ranked_users, start=1):
            user_points = int(by_user.get(ranked_user.id, 0))
            if previous_points is None or user_points < previous_points:
                current_rank = index
                previous_points = user_points
            rank_by_user[ranked_user.id] = current_rank

        for user in self:
            points = int(by_user.get(user.id, 0))
            user.gamification_points = points
            user.gamification_level = self._get_gamification_level(points)
            user.gamification_rank = int(rank_by_user.get(user.id, 0))


class SlideChannelPartner(models.Model):
    _inherit = "slide.channel.partner"

    COURSE_COMPLETION_POINTS = 100

    def _post_completion_update_hook(self, completed=True):
        super()._post_completion_update_hook(completed=completed)

        mission_obj = self.env["academy.gamification.mission"].sudo()

        for membership in self.sudo():
            user = membership.partner_id.user_ids[:1]
            if not user:
                continue

            source_key = f"course_complete:{membership.channel_id.id}:{membership.partner_id.id}"
            mission = mission_obj.search([("source_key", "=", source_key)], limit=1)

            if completed:
                if not mission:
                    mission_obj.create({
                        "name": f"Completed course: {membership.channel_id.name}",
                        "description": "Points granted automatically when a course is completed.",
                        "user_id": user.id,
                        "points": self.COURSE_COMPLETION_POINTS,
                        "state": "done",
                        "completion_date": fields.Date.context_today(self),
                        "source_key": source_key,
                    })
                elif mission.state != "done":
                    mission.write({
                        "state": "done",
                        "completion_date": fields.Date.context_today(self),
                    })
            elif mission and mission.state == "done":
                mission.write({
                    "state": "draft",
                    "completion_date": False,
                })
