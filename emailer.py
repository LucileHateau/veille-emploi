"""
Compose et envoie le mail quotidien récapitulant les nouvelles offres pertinentes.

Utilise Gmail en SMTP avec un "mot de passe d'application" (App Password), stocké
dans les secrets GitHub Actions — jamais en clair dans le code. Voir le README
pour la procédure de création de ce mot de passe.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.settings import EMAIL_SUBJECT

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _format_offer_text(offer: dict) -> str:
    deadline = offer.get("deadline_date") or "non précisée"
    duration = offer.get("contract_duration") or "non précisée"
    lines = [
        f"• {offer.get('title') or 'Offre sans titre'}",
        f"  Site : {offer.get('site_name')}",
        f"  Résumé : {offer.get('summary') or '(pas de résumé disponible)'}",
        f"  Lien : {offer.get('link')}",
        f"  Date limite de candidature : {deadline}",
        f"  Type de contrat : {offer.get('contract_type')}  |  Durée : {duration}",
        f"  Pertinence estimée : {offer.get('relevance_score')}/10+",
        "",
    ]
    return "\n".join(lines)


def _format_offer_html(offer: dict) -> str:
    deadline = offer.get("deadline_date") or "non précisée"
    duration = offer.get("contract_duration") or "non précisée"
    link = offer.get("link") or "#"
    return f"""
    <div style="margin-bottom:18px;padding:14px 16px;border:1px solid #dde3e0;border-radius:8px;">
      <div style="font-size:15px;font-weight:600;color:#1f3d2b;margin-bottom:6px;">
        {offer.get('title') or 'Offre sans titre'}
      </div>
      <div style="font-size:13px;color:#555;margin-bottom:8px;">
        <strong>{offer.get('site_name')}</strong>
      </div>
      <div style="font-size:13px;color:#333;margin-bottom:8px;">
        {offer.get('summary') or '(pas de résumé disponible)'}
      </div>
      <div style="font-size:13px;color:#333;">
        📅 Date limite : <strong>{deadline}</strong> &nbsp;|&nbsp;
        📄 Contrat : <strong>{offer.get('contract_type')}</strong>
        {f" ({duration})" if duration != "non précisée" else ""}
      </div>
      <div style="margin-top:8px;">
        <a href="{link}" style="color:#2f6f4f;font-weight:600;">Voir l'offre en ligne →</a>
      </div>
    </div>
    """


def build_message(new_offers: list[dict], sender: str, recipient: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = sender
    msg["To"] = recipient

    text_body = (
        f"{len(new_offers)} nouvelle(s) offre(s) correspondant à ton profil "
        f"(écologie marine / océanographie / ornithologie marine / pêche) :\n\n"
    )
    text_body += "\n".join(_format_offer_text(o) for o in new_offers)

    html_body = f"""
    <html><body style="font-family:Arial,Helvetica,sans-serif;color:#222;">
      <h2 style="color:#1f3d2b;">{len(new_offers)} nouvelle(s) offre(s) d'emploi</h2>
      <p style="color:#555;">Correspondant à ton profil (écologie marine, océanographie,
      ornithologie marine, pêche — terrain, France ou international).</p>
      {"".join(_format_offer_html(o) for o in new_offers)}
      <p style="font-size:12px;color:#999;margin-top:24px;">
        Généré automatiquement par ton bot de veille emploi (GitHub Actions).
      </p>
    </body></html>
    """

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def send_digest_email(new_offers: list[dict]) -> bool:
    """Envoie le mail. Renvoie True si l'envoi a réussi, False sinon (ou si pas de credentials)."""
    sender = os.environ.get("EMAIL_ADDRESS")
    app_password = os.environ.get("EMAIL_APP_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL", sender)

    if not sender or not app_password:
        print("⚠️  EMAIL_ADDRESS / EMAIL_APP_PASSWORD non définis : envoi de mail ignoré "
              "(voir le README pour configurer les secrets GitHub Actions).")
        return False

    if not new_offers:
        print("Aucune nouvelle offre : pas de mail envoyé.")
        return False

    msg = build_message(new_offers, sender, recipient)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, [recipient], msg.as_string())
        print(f"✅ Mail envoyé à {recipient} avec {len(new_offers)} offre(s).")
        return True
    except smtplib.SMTPException as exc:
        print(f"❌ Échec de l'envoi du mail : {exc}")
        return False
