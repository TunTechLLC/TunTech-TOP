import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from api.db.repositories.reporting import ReportingRepository
from api.db.repositories.pattern import PatternRepository
from api.db.repositories.engagement import EngagementRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_reporting_repo() -> ReportingRepository:
    return ReportingRepository()


def get_pattern_repo() -> PatternRepository:
    return PatternRepository()


@router.get("/cross-engagement")
def get_cross_engagement(repo: ReportingRepository = Depends(get_reporting_repo)):
    """Return all cross-engagement reporting views as structured JSON."""
    return {
        'pattern_frequency':           repo.get_pattern_frequency(),
        'pattern_frequency_by_domain': repo.get_pattern_frequency_by_domain(),
        'accepted_patterns':           repo.get_accepted_patterns(),
        'economic_impact':             repo.get_economic_impact(),
        'agent_run_log':               repo.get_agent_run_log(),
        'engagement_summary':          repo.get_engagement_summary(),
        'engagement_overview':         repo.get_engagement_overview(),
    }


@router.get("/patterns/library")
def get_pattern_library(repo: PatternRepository = Depends(get_pattern_repo)):
    """Return the full pattern library P01-P60.
    Registered under /api prefix so it is not confused with engagement endpoints."""
    return repo.get_library()


@router.get("/{engagement_id}/report/download")
async def download_report(engagement_id: str):
    """Generate and download the OPD Transformation Roadmap Word document.
    Saves to 04_Agent_Outputs folder if derivable from documents_folder path,
    otherwise saves to the system temp directory."""
    from api.services.report_generator import ReportGeneratorService
    from fastapi.responses import FileResponse

    try:
        file_path = await ReportGeneratorService(engagement_id).generate()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Report generation failed for {engagement_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    return FileResponse(
        file_path,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=f"OPD_Transformation_Roadmap_{engagement_id}.docx",
    )


@router.post("/{engagement_id}/report/generate")
async def generate_report(engagement_id: str):
    """Generate the OPD Word report, save it to the engagement's reports_folder,
    and return the saved file path. Does not stream the file to the browser."""
    from api.services.report_generator import ReportGeneratorService

    try:
        file_path = await ReportGeneratorService(engagement_id).generate()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Report generation failed for {engagement_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    return {"saved_to": file_path}


@router.post("/{engagement_id}/report/open-folder")
def open_reports_folder(engagement_id: str):
    """Open the engagement's reports_folder in Windows Explorer.
    Windows-only — uses os.startfile(). No-op on non-Windows platforms.
    When TOP moves to cloud hosting this endpoint will not be called."""
    eng = EngagementRepository().get_by_id(engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    reports_folder = eng.get('reports_folder') or ''
    if not reports_folder:
        raise HTTPException(status_code=400, detail="Reports folder not set. Update engagement settings first.")
    if not os.path.exists(reports_folder):
        raise HTTPException(status_code=400, detail=f"Reports folder does not exist: {reports_folder}")

    if os.name == 'nt':
        os.startfile(reports_folder)

    return {"opened": reports_folder}


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}