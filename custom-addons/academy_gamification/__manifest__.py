{
    "name": "Academy Gamification",
    "summary": "Base module to gamify eLearning with missions and points",
    "version": "18.0.1.0.0",
    "category": "Website/eLearning",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["base", "website_slides", "gamification"],
    "data": [
        "security/ir.model.access.csv",
        "views/academy_mission_views.xml",
        "views/academy_ranking_views.xml",
        "views/academy_decision_backend_views.xml",
        "views/academy_marketing_website_templates.xml",
        "views/academy_decision_website_templates.xml",
        "views/academy_decision_report.xml",
        "data/fundador_digital_data.xml"
    ],
    "application": True,
    "installable": True
}
