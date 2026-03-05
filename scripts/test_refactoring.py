"""RfP evaluation system integration test."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_pdf_strategies():
    """Test PDF strategies."""
    print("\n" + "=" * 60)
    print("1. PDF Strategy Test")
    print("=" * 60)
    
    try:
        from app.domain.shared.pdf import PDFContext, PDFFactory
        
        strategy = PDFFactory.get_default_for_text()
        print("[OK] PyMuPDF strategy created")
        
        strategy = PDFFactory.get_default_for_tables()
        print("[OK] pdfplumber strategy created")
        
        with PDFContext.create("pymupdf") as pdf:
            print("[OK] PyMuPDF context created")
        
        with PDFContext.create("pdfplumber") as pdf:
            print("[OK] pdfplumber context created")
        
        print("\n[PASS] PDF Strategy Test")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] PDF Strategy Test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rfp_domain():
    """Test RfP domain."""
    print("\n" + "=" * 60)
    print("2. RfP Domain Test")
    print("=" * 60)
    
    try:
        from app.domain.rfp import (
            RfPService,
            RfPPDFParser,
            RequirementRepository,
            RequirementType,
            RequirementPriority,
        )
        
        service = RfPService()
        print("[OK] RfPService created")
        
        parser = RfPPDFParser(use_pdfplumber=True)
        print("[OK] RfPPDFParser created")
        
        repo = RequirementRepository()
        print("[OK] RequirementRepository created")
        
        req_type = RequirementType.TECHNICAL
        priority = RequirementPriority.MANDATORY
        print("[OK] Enums defined")
        
        print("\n[PASS] RfP Domain Test")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] RfP Domain Test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_proposal_domain():
    """Test Proposal domain."""
    print("\n" + "=" * 60)
    print("3. Proposal Domain Test")
    print("=" * 60)
    
    try:
        from app.domain.proposal import (
            ProposalService,
            ProposalPDFParser,
            SectionType,
        )
        
        service = ProposalService()
        print("[OK] ProposalService created")
        
        parser = ProposalPDFParser(use_pdfplumber=True)
        print("[OK] ProposalPDFParser created")
        
        section_type = SectionType.EXECUTIVE_SUMMARY
        print("[OK] Enums defined")
        
        print("\n[PASS] Proposal Domain Test")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Proposal Domain Test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evaluation_domain():
    """Test Evaluation domain."""
    print("\n" + "=" * 60)
    print("4. Evaluation Domain Test")
    print("=" * 60)
    
    try:
        from app.domain.evaluation import (
            EvaluationOrchestrator,
            Matcher,
            RuleValidator,
            ReportGenerator,
            MatchStatus,
            EvaluationScore,
        )
        
        orchestrator = EvaluationOrchestrator()
        print("[OK] EvaluationOrchestrator created")
        
        matcher = Matcher()
        print("[OK] Matcher created")
        
        validator = RuleValidator()
        print("[OK] RuleValidator created")
        
        generator = ReportGenerator()
        print("[OK] ReportGenerator created")
        
        status = MatchStatus.FULLY_MATCHED
        score = EvaluationScore.EXCELLENT
        print("[OK] Enums defined")
        
        print("\n[PASS] Evaluation Domain Test")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Evaluation Domain Test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_router():
    """Test API router."""
    print("\n" + "=" * 60)
    print("5. API Router Test")
    print("=" * 60)
    
    try:
        from app.api.v1.evaluation.evaluation_router import router
        
        print("[OK] Evaluation router imported")
        print(f"  - Prefix: {router.prefix}")
        print(f"  - Tags: {router.tags}")
        print(f"  - Routes: {len(router.routes)} endpoints")
        
        print("\n[PASS] API Router Test")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] API Router Test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("RfP Evaluation System - Integration Test")
    print("=" * 60)
    
    results = []
    
    results.append(("PDF Strategy", test_pdf_strategies()))
    results.append(("RfP Domain", test_rfp_domain()))
    results.append(("Proposal Domain", test_proposal_domain()))
    results.append(("Evaluation Domain", test_evaluation_domain()))
    results.append(("API Router", test_api_router()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
    
    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)
    
    print(f"\nTotal: {passed_count}/{total} passed")
    
    if passed_count == total:
        print("\nAll tests passed!")
        return 0
    else:
        print(f"\n{total - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
