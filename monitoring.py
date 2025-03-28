import highlight_io
import logging
from datetime import datetime

def init_highlight(project_id, environment_name, service_name):
    return highlight_io.H(
        project_id=project_id,
        instrument_logging=True,
        service_name=service_name,
        environment=environment_name,
    )


def _send_failure_notification(highlight_io, error_details="No error details provided", meeting_log={}):
    error_details = {
        "message": f"Google Meeting Bot Processing Failed",
        "meetlink": meeting_log.get("meetlink", "unknown"),
        "start_time_utc": meeting_log.get("start_time_utc", "unknown"),
        "recording_start_time": meeting_log.get("end_time_utc", "unknown"),
        "error_details": error_details,
        "failed_at": str(datetime.now()),
        "severity": "error",
    }

    try:
        raise Exception(f"Google Meeting Bot processing failed: {error_details}")
    except Exception as e:
        if highlight_io:
            highlight_io.record_exception(e)
        logging.exception("Exception recorded in Highlight.io")