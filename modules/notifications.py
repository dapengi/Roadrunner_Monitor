"""
Email notification functions
"""

import smtplib
import datetime
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENTS

logger = logging.getLogger(__name__)


def format_meeting_date_for_email(meeting_date):
    """Format meeting date for email display (e.g., Tuesday, July 1, 2025)."""
    try:
        if not meeting_date or len(meeting_date) != 6:
            return datetime.datetime.now().strftime('%A, %B %d, %Y')
        
        # Parse MMDDYY format
        mm = int(meeting_date[:2])
        dd = int(meeting_date[2:4])
        yy = int(meeting_date[4:6])
        
        # Assume 20xx for years
        yyyy = 2000 + yy if yy < 50 else 1900 + yy
        
        # Create date object and format
        date_obj = datetime.datetime(yyyy, mm, dd)
        return date_obj.strftime('%A, %B %d, %Y')
        
    except Exception as e:
        logger.warning(f"Error formatting meeting date: {e}")
        return datetime.datetime.now().strftime('%A, %B %d, %Y')


def format_meeting_date_for_subject(meeting_date):
    """Format meeting date for email subject (e.g., 7/1/25)."""
    try:
        if not meeting_date or len(meeting_date) != 6:
            now = datetime.datetime.now()
            return f"{now.month}/{now.day}/{now.year % 100}"
        
        # Parse MMDDYY format
        mm = int(meeting_date[:2])
        dd = int(meeting_date[2:4])
        yy = int(meeting_date[4:6])
        
        return f"{mm}/{dd}/{yy}"
        
    except Exception as e:
        logger.warning(f"Error formatting meeting date for subject: {e}")
        now = datetime.datetime.now()
        return f"{now.month}/{now.day}/{now.year % 100}"


def send_notification(new_entries, transcript_results=None):
    """Send HTML email notification about new entries with Nextcloud links."""
    if not all([EMAIL_USER, EMAIL_PASSWORD]):
        logger.warning("Email configuration missing. Skipping notification.")
        return
    
    try:
        for recipient in EMAIL_RECIPIENTS:
            for i, entry in enumerate(new_entries):
                # Get transcript result for this entry
                result = transcript_results[i] if transcript_results and i < len(transcript_results) else None
                
                if not result:
                    logger.warning(f"No transcript result for entry {i}, skipping email")
                    continue
                
                # Extract meeting information
                meeting_info = result.get('meeting_info', {})
                committee_name = meeting_info.get('committee_name', 'Unknown Committee')
                
                # Get meeting date and time from result
                meeting_date = result.get('meeting_date')
                meeting_time = result.get('meeting_time', 'Time not available')
                
                # Format dates for email
                formatted_date = format_meeting_date_for_email(meeting_date)
                subject_date = format_meeting_date_for_subject(meeting_date)
                
                # Create email
                msg = MIMEMultipart('alternative')
                msg['From'] = EMAIL_USER
                msg['To'] = recipient
                msg['Subject'] = f"New Legislature Transcript - {committee_name} - {subject_date}"
                
                # HTML email template
                html_template = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="en">
<head>
<title></title>
<meta charset="UTF-8" />
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<!--[if !mso]>-->
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<!--<![endif]-->
<meta name="x-apple-disable-message-reformatting" content="" />
<meta content="target-densitydpi=device-dpi" name="viewport" />
<meta content="true" name="HandheldFriendly" />
<meta content="width=device-width" name="viewport" />
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no, url=no" />
<style type="text/css">
table {
border-collapse: separate;
table-layout: fixed;
mso-table-lspace: 0pt;
mso-table-rspace: 0pt
}
table td {
border-collapse: collapse
}
.ExternalClass {
width: 100%
}
.ExternalClass,
.ExternalClass p,
.ExternalClass span,
.ExternalClass font,
.ExternalClass td,
.ExternalClass div {
line-height: 100%
}
body, a, li, p, h1, h2, h3 {
-ms-text-size-adjust: 100%;
-webkit-text-size-adjust: 100%;
}
html {
-webkit-text-size-adjust: none !important
}
body, #innerTable {
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale
}
#innerTable img+div {
display: none;
display: none !important
}
img {
Margin: 0;
padding: 0;
-ms-interpolation-mode: bicubic
}
h1, h2, h3, p, a {
line-height: inherit;
overflow-wrap: normal;
white-space: normal;
word-break: break-word
}
a {
text-decoration: none
}
h1, h2, h3, p {
min-width: 100%!important;
width: 100%!important;
max-width: 100%!important;
display: inline-block!important;
border: 0;
padding: 0;
margin: 0
}
a[x-apple-data-detectors] {
color: inherit !important;
text-decoration: none !important;
font-size: inherit !important;
font-family: inherit !important;
font-weight: inherit !important;
line-height: inherit !important
}
u + #body a {
color: inherit;
text-decoration: none;
font-size: inherit;
font-family: inherit;
font-weight: inherit;
line-height: inherit;
}
a[href^="mailto"],
a[href^="tel"],
a[href^="sms"] {
color: inherit;
text-decoration: none
}
</style>
<style type="text/css">
@media (min-width: 481px) {
.hd { display: none!important }
}
</style>
<style type="text/css">
@media (max-width: 480px) {
.hm { display: none!important }
}
</style>
<style type="text/css">
@media (max-width: 480px) {
.t5{mso-line-height-alt:0px!important;line-height:0!important;display:none!important}.t6{border-top-left-radius:0!important;border-top-right-radius:0!important}.t56{border-bottom-right-radius:0!important;border-bottom-left-radius:0!important}
}
</style>
<!--[if !mso]>-->
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&amp;display=swap" rel="stylesheet" type="text/css" />
<!--<![endif]-->
<!--[if mso]>
<xml>
<o:OfficeDocumentSettings>
<o:AllowPNG/>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml>
<![endif]-->
</head>
<body id="body" class="t63" style="min-width:100%;Margin:0px;padding:0px;background-color:#292929;"><div class="t62" style="background-color:#292929;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" align="center"><tr><td class="t61" style="font-size:0;line-height:0;mso-line-height-rule:exactly;background-color:#292929;" valign="top" align="center">
<!--[if mso]>
<v:background xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false">
<v:fill color="#292929"/>
</v:background>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" align="center" id="innerTable"><tr><td><div class="t5" style="mso-line-height-rule:exactly;mso-line-height-alt:100px;line-height:100px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t9" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="600" class="t8" style="width:600px;">
<table class="t7" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t6" style="overflow:hidden;background-color:#D0D7E2;padding:40px 0 40px 0;border-radius:14px 14px 0 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100% !important;"><tr><td align="center">
<table class="t4" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="256" class="t3" style="width:256px;">
<table class="t2" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t1" style="text-align:center;padding:10px;"><div style="font-size:0px;line-height:0;"><a href="https://lwe.vote/" target="_blank" style="text-decoration:none;display:inline-block;"><img class="t0" style="display:block;border:0;height:auto;width:180px;max-width:180px;margin:0 auto;" width="180" height="47" alt="LWE.Vote - Legislative Monitoring System" src="https://res.cloudinary.com/dah7l8ct2/image/upload/f_png,w_360,h_94,c_fit,q_85/v1753387743/logo_vqok6w.png" border="0"/></a></div></td></tr></table>
</td></tr></table>
</td></tr></table></td></tr></table>
</td></tr></table>
</td></tr><tr><td align="center">
<table class="t59" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="600" class="t58" style="width:600px;">
<table class="t57" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t56" style="overflow:hidden;background-color:#FFFFFF;padding:40px 30px 40px 30px;border-radius:0 0 14px 14px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100% !important;"><tr><td align="center">
<table class="t14" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="540" class="t13" style="width:600px;">
<table class="t12" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t11"><p class="t10" style="margin:0;Margin:0;font-family:Roboto,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:400;font-style:normal;font-size:16px;text-decoration:none;text-transform:none;direction:ltr;color:#333333;text-align:left;mso-line-height-rule:exactly;mso-text-raise:2px;">Hello,</p></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t15" style="mso-line-height-rule:exactly;mso-line-height-alt:13px;line-height:13px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t20" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="540" class="t19" style="width:600px;">
<table class="t18" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t17"><p class="t16" style="margin:0;Margin:0;font-family:Roboto,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:400;font-style:normal;font-size:16px;text-decoration:none;text-transform:none;direction:ltr;color:#333333;text-align:left;mso-line-height-rule:exactly;mso-text-raise:2px;">A new legislative committee meeting has been processed and transcribed:</p></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t21" style="mso-line-height-rule:exactly;mso-line-height-alt:11px;line-height:11px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t35" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="540" class="t34" style="width:600px;">
<table class="t33" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t32"><p class="t31" style="margin:0;Margin:0;font-family:Roboto,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:400;font-style:normal;font-size:16px;text-decoration:none;text-transform:none;direction:ltr;color:#333333;text-align:left;mso-line-height-rule:exactly;mso-text-raise:2px;"><span class="t22" style="margin:0;Margin:0;font-weight:700;mso-line-height-rule:exactly;">Committee:</span> {COMMITTEE_NAME} Meeting <br/><span class="t23" style="margin:0;Margin:0;font-weight:700;mso-line-height-rule:exactly;">Date:</span> {MEETING_DATE}<br/><span class="t24" style="margin:0;Margin:0;font-weight:700;mso-line-height-rule:exactly;">Time:</span> {MEETING_TIME} <br/><span class="t25" style="margin:0;Margin:0;font-weight:700;mso-line-height-rule:exactly;">Status:</span> {STATUS} <br/><span class="t26" style="margin:0;Margin:0;font-weight:700;mso-line-height-rule:exactly;">Video Source:</span> <a class="t30" href="{VIDEO_SOURCE_URL}" style="margin:0;Margin:0;font-weight:700;font-style:normal;text-decoration:none;direction:ltr;color:#0000FF;mso-line-height-rule:exactly;" target="_blank">View Meeting Recording</a><br/><span class="t29" style="margin:0;Margin:0;color:#333333;mso-line-height-rule:exactly;"><span class="t27" style="margin:0;Margin:0;font-weight:700;mso-line-height-rule:exactly;">Processed at:</span><span class="t28" style="margin:0;Margin:0;font-weight:400;mso-line-height-rule:exactly;"> {PROCESSING_TIME}</span></span></p></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t36" style="mso-line-height-rule:exactly;mso-line-height-alt:15px;line-height:15px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t43" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="540" class="t42" style="width:600px;">
<table class="t41" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t40"><p class="t39" style="margin:0;Margin:0;font-family:Roboto,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:400;font-style:normal;font-size:16px;text-decoration:none;text-transform:none;direction:ltr;color:#333333;text-align:left;mso-line-height-rule:exactly;mso-text-raise:2px;">The transcript is now available for internal use at the following link: <a class="t38" href="{NEXTCLOUD_LINK}" style="margin:0;Margin:0;font-weight:700;font-style:normal;text-decoration:none;direction:ltr;color:#0000FF;mso-line-height-rule:exactly;" target="_blank"><span class="t37" style="margin:0;Margin:0;mso-line-height-rule:exactly;">Access Transcript</span></a></p></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t44" style="mso-line-height-rule:exactly;mso-line-height-alt:25px;line-height:25px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t49" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="540" class="t48" style="width:600px;">
<table class="t47" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t46"><p class="t45" style="margin:0;Margin:0;font-family:Roboto,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:400;font-style:normal;font-size:16px;text-decoration:none;text-transform:none;direction:ltr;color:#333333;text-align:left;mso-line-height-rule:exactly;mso-text-raise:2px;">Enjoy!</p></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t50" style="mso-line-height-rule:exactly;mso-line-height-alt:6px;line-height:6px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t55" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="540" class="t54" style="width:600px;">
<table class="t53" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t52"><p class="t51" style="margin:0;Margin:0;font-family:Roboto,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:400;font-style:normal;font-size:16px;text-decoration:none;text-transform:none;direction:ltr;color:#333333;text-align:left;mso-line-height-rule:exactly;mso-text-raise:2px;"><a href="https://lwe.vote/" target="_blank" style="color:#333333;text-decoration:none;">LWE.Vote</a></p></td></tr></table>
</td></tr></table>
</td></tr></table></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t60" style="mso-line-height-rule:exactly;mso-line-height-alt:80px;line-height:80px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr></table></td></tr></table></div><div class="gmail-fix" style="display: none; white-space: nowrap; font: 15px courier; line-height: 0;">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;</div></body>
</html>'''
                
                # Replace placeholders with actual data
                processing_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S MST')
                
                # Determine status based on transcript result
                status = "Transcription Complete"
                if result.get('share_link'):
                    status += " & Available"
                
                html_content = html_template.replace('{COMMITTEE_NAME}', committee_name)
                html_content = html_content.replace('{MEETING_DATE}', formatted_date)
                html_content = html_content.replace('{MEETING_TIME}', meeting_time)
                html_content = html_content.replace('{STATUS}', status)
                html_content = html_content.replace('{VIDEO_SOURCE_URL}', entry.get('link', '#'))
                html_content = html_content.replace('{PROCESSING_TIME}', processing_time)
                # Handle None value for share_link (e.g., when rate limited)
                share_link = result.get('share_link') or '#'
                html_content = html_content.replace('{NEXTCLOUD_LINK}', share_link)
                
                # Create HTML part
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
                
                # Send email
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                logger.info(f"HTML notification email sent successfully to {recipient} for {committee_name}")
                
    except Exception as e:
        logger.error(f"Error sending HTML notification: {e}")
