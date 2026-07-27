import re

from markupsafe import Markup

from odoo import api, models, _


DIRECT_VIDEO_URL_REGEX = re.compile(r".*\.(mp4|webm|ogg|mov|m4v)(?:\?.*)?$", re.IGNORECASE)


class AcademyMinioSlide(models.Model):
    _inherit = 'slide.slide'

    @api.depends('slide_category', 'google_drive_id', 'video_source_type', 'youtube_id')
    def _compute_embed_code(self):
        super()._compute_embed_code()
        for slide in self:
            if slide.slide_category != 'video' or slide.embed_code or not slide.video_url:
                continue

            if DIRECT_VIDEO_URL_REGEX.match(slide.video_url) or 'minio' in slide.video_url.lower() or ':9000/' in slide.video_url:
                embed_code = Markup(
                    '<video controls playsinline preload="metadata" '
                    'style="width: 100%; max-height: 75vh; background: #000; border-radius: 0.75rem;" '
                    'aria-label="%s">'
                    '<source src="%s" />'
                    '</video>'
                ) % (_('Course video'), slide.video_url)
                slide.embed_code = embed_code
                slide.embed_code_external = embed_code