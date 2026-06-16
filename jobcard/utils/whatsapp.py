import requests
from django.conf import settings

MSG91_BASE_URL = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
MSG91_NAMESPACE = "683224fe_6390_4c6c_b4b0_179dfbaadd9f"
MSG91_INTEGRATED_NUMBER = "917907421354"


def _format_mobile(mobile):
    """MSG91 expects country code with no '+' (e.g. 919876543210)."""
    digits = "".join(ch for ch in str(mobile) if ch.isdigit())
    if len(digits) == 10:
        return f"91{digits}"
    return digits


def _post_template(template_name, to_mobile, components):
    payload = {
        "integrated_number": MSG91_INTEGRATED_NUMBER,
        "content_type": "template",
        "payload": {
            "messaging_product": "whatsapp",
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en", "policy": "deterministic"},
                "namespace": MSG91_NAMESPACE,
                "to_and_components": [
                    {
                        "to": [_format_mobile(to_mobile)],
                        "components": components,
                    }
                ],
            },
        },
    }
    headers = {
        "Content-Type": "application/json",
        "authkey": settings.MSG91_AUTH_KEY,
    }
    return requests.post(MSG91_BASE_URL, json=payload, headers=headers, timeout=20)


def send_quotation_whatsapp(*, mobile, customer_name, quotation_url, garage_name):
    """Quotation is shared as a link, not a file."""
    components = {
        "body_1": {"type": "text", "value": customer_name},
        "body_2": {"type": "text", "value": quotation_url},
        "body_3": {"type": "text", "value": garage_name},
    }
    return _post_template("digiauto", mobile, components)


def send_invoice_whatsapp(*, mobile, customer_name, garage_name, pdf_url, filename):
    """Invoice is shared as an actual PDF document."""
    components = {
        "header_1": {"type": "document", "filename": filename, "value": pdf_url},
        "body_1": {"type": "text", "value": customer_name},
        "body_2": {"type": "text", "value": garage_name},
    }
    return _post_template("digiauto_invoice", mobile, components)