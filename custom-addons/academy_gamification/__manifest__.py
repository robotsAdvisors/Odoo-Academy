{
    "name": "Academy Gamification",
    "summary": "Base module to gamify eLearning with missions and points",
    "version": "18.0.1.0.0",
    "category": "Website/eLearning",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["base", "website_slides", "gamification", "sale", "payment", "portal", "auth_signup"],
    "data": [
        "security/ir.model.access.csv",
        "data/fundador_digital_data.xml",
        "views/academy_mission_views.xml",
        "views/academy_ranking_views.xml",
        "views/academy_decision_backend_views.xml",
        "views/academy_marketing_website_templates.xml",
        "views/academy_decision_website_templates.xml",
        "views/academy_decision_report.xml",
        "views/academy_inscripcion_templates.xml"
    ],
    "application": True,
    "installable": True
}
