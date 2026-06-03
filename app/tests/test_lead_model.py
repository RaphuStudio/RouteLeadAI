from app.models.lead import Lead, LeadSource, LeadStatus

def test_lead_creation():
    lead = Lead(
        source=LeadSource.WEBSITE,
        raw_content="Test content",
        company_name="Test Co",
        contact_name="John Doe"
    )
    assert lead.id is not None
    assert lead.status == LeadStatus.NEW
    assert lead.intent_score == 0

def test_lead_scores():
    lead = Lead(
        source=LeadSource.CHAT,
        raw_content="Test",
        company_name="Test Co",
        budget_score=20,
        authority_score=15,
        need_score=25,
        timeline_score=18
    )
    assert lead.budget_score == 20
    assert lead.authority_score == 15
    assert lead.need_score == 25
    assert lead.timeline_score == 18