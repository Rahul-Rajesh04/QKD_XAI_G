__author__ = "Rahul Rajesh 2360445"

import os
import csv
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_incident_report(
    vitals: dict, 
    verdict: str, 
    rf_pred: str, 
    rf_conf: float, 
    svm_anomaly: bool, 
    class_probs: dict, 
    report_text: str, 
    image_path: str = None
) -> str:
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_dir = os.path.join(project_root, "Results", "Incident_Reports")
    os.makedirs(report_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    doc_hash = hashlib.sha256(f"{timestamp}{verdict}{vitals.get('qber', 0)}".encode()).hexdigest()[:16].upper()
    filename = f"{timestamp}_SESSION_AUDIT_REPORT.pdf"
    filepath = os.path.join(report_dir, filename)
    
    doc = SimpleDocTemplate(
        filepath, 
        pagesize=letter,
        rightMargin=0.4*inch, leftMargin=0.4*inch,
        topMargin=0.4*inch, bottomMargin=0.4*inch
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', fontName='Courier-Bold', fontSize=18, leading=22, textColor=colors.HexColor("#ff003c"), spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitle', fontName='Courier', fontSize=8, leading=10, textColor=colors.HexColor("#555555"), spaceAfter=15)
    section_style = ParagraphStyle('Section', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.whitesmoke, spaceBefore=0, spaceAfter=0)
    normal_style = ParagraphStyle('NormalText', fontName='Helvetica', fontSize=9, leading=11, spaceAfter=2)
    terminal_style = ParagraphStyle('Terminal', fontName='Courier', fontSize=8, leading=10, textColor=colors.HexColor("#00ff66"))
    log_style = ParagraphStyle('LogText', fontName='Courier', fontSize=7, leading=8, textColor=colors.black)

    elements = []
    
    elements.append(Paragraph("QKD CRYPTOGRAPHIC INTRUSION & ANOMALY REPORT", title_style))
    elements.append(Paragraph(f"CLASSIFIED AUDIT DOCUMENT // REF-HASH: {doc_hash}", subtitle_style))
    
    log_path = os.path.join(project_root, "logs", "threat_telemetry.csv")
    total_events = 0
    attack_events = 0
    history_data = [["Timestamp", "Verdict", "Signature", "Conf.", "QBER"]]
    
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            rows = list(reader)
            total_events = len(rows)
            for row in rows:
                if len(row) >= 8:
                    v_text = row[1].upper()
                    if "ATTACK" in v_text or "ZERO-DAY" in v_text or "ABORT" in v_text:
                        attack_events += 1
            
            for row in rows[-15:]:
                if len(row) >= 8:
                    history_data.append([
                        Paragraph(row[0], log_style),
                        Paragraph(row[1], log_style),
                        Paragraph(row[2], log_style),
                        Paragraph(row[3], log_style),
                        Paragraph(row[7], log_style)
                    ])

    verdict_color = "#ff003c" if ("ATTACK" in verdict.upper() or "ZERO-DAY" in verdict.upper() or "ABORT" in verdict.upper()) else "#00ff66"
    if "WARNING" in verdict.upper(): verdict_color = "#fcee0a"

    meta_data = [
        ["REPORT GENERATED:", f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST", "PROTOCOL:", "BB84 Decoy-State"],
        ["OPERATOR ID:", "Rahul Rajesh (2360445)", "WAVELENGTH:", "1550 nm (ITU-T G.652)"],
        ["SESSION EVENTS:", str(total_events), "THREATS LOGGED:", str(attack_events)],
        ["SYSTEM VERDICT:", Paragraph(f"<b><font color='{verdict_color}'>{verdict.upper()}</font></b>", normal_style), "CRYPTO STATUS:", "KEY MATERIAL FLUSHED" if attack_events > 0 else "NOMINAL"]
    ]
    
    meta_table = Table(meta_data, colWidths=[1.5*inch, 2.5*inch, 1.3*inch, 2.3*inch])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor("#555555")),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor("#555555")),
        ('TEXTCOLOR', (1,0), (1,2), colors.black),
        ('TEXTCOLOR', (3,0), (3,2), colors.black),
        ('TEXTCOLOR', (3,3), (3,3), colors.HexColor("#ff003c") if attack_events > 0 else colors.HexColor("#00ff66")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor("#ff003c")), 
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.15*inch))
    
    def make_section_header(title):
        t = Table([[Paragraph(title, section_style)]], colWidths=[7.6*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1a1a1a")),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        return t

    elements.append(make_section_header("1. DUAL-ENGINE MACHINE LEARNING THREAT RESOLUTION"))
    elements.append(Spacer(1, 0.05*inch))
    
    svm_status = "ANOMALY DETECTED (Out-of-Distribution)" if svm_anomaly else "NORMAL (In-Distribution)"
    svm_font_color = "#ff003c" if svm_anomaly else "#00ff66"
    
    ai_data = [
        ["Signature Engine (RF Classifier):", rf_pred.upper(), f"Confidence: {rf_conf * 100:.2f}%"],
        ["Anomaly Engine (OC-SVM Boundary):", Paragraph(f"<b><font color='{svm_font_color}'>{svm_status}</font></b>", normal_style), "Boolean Trigger"]
    ]
    ai_table = Table(ai_data, colWidths=[2.2*inch, 3.8*inch, 1.6*inch])
    ai_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,0), 0.5, colors.lightgrey),
    ]))
    elements.append(ai_table)
    elements.append(Spacer(1, 0.15*inch))
    
    elements.append(make_section_header("2. QUANTUM HARDWARE TELEMETRY DEVIATION MATRIX"))
    elements.append(Spacer(1, 0.05*inch))

    v_val = vitals.get('voltage', 0)
    j_val = vitals.get('jitter', 0)
    q_val = vitals.get('qber', 0)
    
    v_dev = v_val - 3.30
    j_dev = j_val - 1.20
    q_dev = (q_val * 100) - 2.50

    telemetry_data = [
        ["Metric", "Observed Value", "Nominal Baseline", "Calculated Deviation Δ"],
        ["Detector Bias Voltage", f"{v_val:.2f} V", "3.30 V", f"{v_dev:+.2f} V"],
        ["Avalanche Timing Jitter", f"{j_val:.3f} ns", "1.200 ns", f"{j_dev:+.3f} ns"],
        ["Quantum Bit Error Rate", f"{q_val * 100:.2f}%", "2.50%", f"{q_dev:+.2f}%"]
    ]
    tel_table = Table(telemetry_data, colWidths=[2.2*inch, 1.8*inch, 1.8*inch, 1.8*inch])
    tel_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,0), (-1,0), 1.0, colors.black),
        ('LINEBELOW', (0,1), (-1,-2), 0.5, colors.lightgrey),
    ]))
    elements.append(tel_table)
    elements.append(Spacer(1, 0.15*inch))

    elements.append(make_section_header("3. FORENSIC NARRATIVE & DECISION LOGIC"))
    elements.append(Spacer(1, 0.05*inch))
    
    clean_text = report_text.replace('\n', '<br/>')
    keywords = ["FORENSIC ANALYSIS:", "CRITICAL THREAT:", "SYSTEM SECURE", "Reasoning:", "Evidence A:", "Evidence B:", "Conclusion:", "Status:", "ANOMALY:", "CRITICAL SYSTEM ABORT", "ELEVATED NOISE WARNING"]
    for kw in keywords:
        clean_text = clean_text.replace(kw, f"<b>{kw}</b>")
        
    narrative_p = Paragraph(clean_text, terminal_style)
    narrative_table = Table([[narrative_p]], colWidths=[7.6*inch])
    narrative_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0a0a0a")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#333333")),
    ]))
    elements.append(narrative_table)
    elements.append(Spacer(1, 0.15*inch))

    if image_path and os.path.exists(image_path) and rf_pred != "normal":
        elements.append(make_section_header("4. SHAP EXPLAINABLE AI VISUAL EVIDENCE"))
        elements.append(Spacer(1, 0.05*inch))
        img = RLImage(image_path, width=5.5*inch, height=3.0*inch, kind='proportional')
        img_table = Table([[img]], colWidths=[7.6*inch])
        img_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        elements.append(img_table)
        elements.append(Spacer(1, 0.15*inch))

    elements.append(make_section_header("5. AUTOMATED TELEMETRY AUDIT (LAST 15 EVENTS)"))
    elements.append(Spacer(1, 0.05*inch))
    
    if len(history_data) > 1:
        hist_table = Table(history_data, colWidths=[1.5*inch, 2.2*inch, 2.0*inch, 0.9*inch, 1.0*inch])
        hist_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f0f0f0")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 3),
        ]))
        elements.append(hist_table)
    else:
        elements.append(Paragraph("No events logged.", normal_style))
        
    doc.build(elements)
    return filepath