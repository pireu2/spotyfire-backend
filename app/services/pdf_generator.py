import io
import base64
from datetime import datetime
from fpdf import FPDF
from typing import Dict, Optional
import requests
from PIL import Image
import re

def normalize_romanian_text(text: str) -> str:
    """Replace Romanian special characters with ASCII equivalents for PDF compatibility."""
    replacements = {
        'ă': 'a', 'Ă': 'A',
        'â': 'a', 'Â': 'A',
        'î': 'i', 'Î': 'I',
        'ș': 's', 'Ș': 'S',
        'ț': 't', 'Ț': 'T'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def parse_markdown_to_pdf(pdf: FPDF, text: str):
    """Parse simple markdown and add to PDF."""
    text = normalize_romanian_text(text)
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(3)
            continue
        
        if pdf.get_y() > 250:
            pdf.add_page()
        
        if line.startswith('### '):
            pdf.set_font('Times', 'B', 11)
            pdf.set_x(10)
            pdf.multi_cell(0, 6, line[4:])
            pdf.ln(2)
        elif line.startswith('## '):
            pdf.set_font('Times', 'B', 12)
            pdf.set_x(10)
            pdf.multi_cell(0, 7, line[3:])
            pdf.ln(3)
        elif line.startswith('# '):
            pdf.set_font('Times', 'B', 13)
            pdf.set_x(10)
            pdf.multi_cell(0, 8, line[2:])
            pdf.ln(3)
        elif line.startswith('- ') or line.startswith('* '):
            pdf.set_font('Times', '', 9)
            pdf.set_x(10)
            pdf.cell(10, 5, '  •', 0, 0)
            pdf.multi_cell(0, 5, line[2:])
        elif line.startswith('**') and line.endswith('**'):
            pdf.set_font('Times', 'B', 9)
            pdf.set_x(10)
            pdf.multi_cell(0, 5, line[2:-2])
        else:
            pdf.set_font('Times', '', 9)
            pdf.set_x(10)
            pdf.multi_cell(0, 5, line)

class ReportPDF(FPDF):
    def header(self):
        self.set_font('Times', 'B', 16)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, 'SpotyFire', 0, 1, 'C')
        self.set_font('Times', '', 10)
        self.cell(0, 6, 'Raport Oficial de Analiza Satelit - Evaluare Daune', 0, 1, 'C')
        self.ln(6)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.set_text_color(0, 0, 0)
        self.cell(0, 5, f'Generat de SpotyFire - {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.cell(0, 5, f'Pagina {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title: str):
        self.set_font('Times', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, normalize_romanian_text(title), 0, 1, 'L')
        self.ln(2)
    
    def section_text(self, label: str, value: str, bold_value: bool = False):
        self.set_font('Times', 'B', 10)
        self.set_text_color(0, 0, 0)
        self.cell(70, 6, normalize_romanian_text(label), 0, 0)
        if bold_value:
            self.set_font('Times', 'B', 10)
        else:
            self.set_font('Times', '', 10)
        self.cell(0, 6, normalize_romanian_text(value), 0, 1)

def generate_satellite_report_pdf(
    property_name: str,
    analysis_data: Dict,
    property_data: Dict,
    overlay_before_b64: Optional[str] = None,
    overlay_after_b64: Optional[str] = None,
    ai_insights: Optional[str] = None
) -> bytes:
    pdf = ReportPDF()
    pdf.add_page()
    
    pdf.chapter_title('INFORMATII GENERALE')
    
    pdf.section_text('Teren:', property_name, bold_value=True)
    pdf.section_text('Data Generarii:', datetime.now().strftime("%d/%m/%Y %H:%M"))
    pdf.section_text('Tip Cultura:', property_data.get('crop_type', 'N/A'))
    pdf.section_text('Suprafata Totala:', f'{property_data.get("area_ha", 0):.2f} ha')
    pdf.section_text('Coordonate:', f'{property_data.get("center_lat"):.6f}, {property_data.get("center_lng"):.6f}')
    pdf.ln(8)
    
    pdf.chapter_title('PERIOADA DE ANALIZA')
    pdf.section_text('Data Incident:', analysis_data.get('incident_date', 'N/A'), bold_value=True)
    pdf.section_text('Perioada Inainte:', f'{analysis_data.get("before_date")} - {analysis_data.get("incident_date")}')
    pdf.section_text('Perioada Dupa:', f'{analysis_data.get("incident_date")} - {analysis_data.get("after_date")}')
    pdf.ln(8)
    
    pdf.chapter_title('REZULTATE ANALIZA SATELIT')
    
    damage_percent = analysis_data.get('damage_percent', 0)
    pdf.section_text('Procent Deteriorare:', f'{damage_percent:.2f}%', bold_value=True)
    pdf.section_text('Zona Afectata:', f'{analysis_data.get("damaged_area_ha", 0):.2f} hectare', bold_value=True)
    pdf.section_text('Cost Estimat Daune:', f'{analysis_data.get("estimated_cost", 0):,.0f} RON', bold_value=True)
    
    if analysis_data.get('ndvi_before') and analysis_data.get('ndvi_after'):
        pdf.ln(4)
        pdf.section_text('NDVI Inainte de Incident:', f'{analysis_data.get("ndvi_before"):.3f}')
        pdf.section_text('NDVI Dupa Incident:', f'{analysis_data.get("ndvi_after"):.3f}')
    
    pdf.ln(10)
    
    print(f"DEBUG: overlay_before_b64 length: {len(overlay_before_b64) if overlay_before_b64 else 0}")
    print(f"DEBUG: overlay_after_b64 length: {len(overlay_after_b64) if overlay_after_b64 else 0}")
    
    if overlay_before_b64:
        try:
            pdf.add_page()
            pdf.chapter_title('ANALIZA INAINTE DE INCIDENT')
            
            before_date = analysis_data.get('before_date', 'N/A')
            incident_date = analysis_data.get('incident_date', 'N/A')
            
            pdf.set_font('Times', 'B', 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, normalize_romanian_text(f'Perioada: {before_date} - {incident_date}'), 0, 1, 'L')
            pdf.ln(5)
            
            if analysis_data.get('ndvi_before'):
                pdf.section_text('NDVI Mediu:', f'{analysis_data.get("ndvi_before"):.3f}')
            pdf.section_text('Suprafata Totala:', f'{analysis_data.get("total_area_ha", 0):.2f} ha')
            pdf.ln(10)
            
            print(f"DEBUG: Processing before overlay")
            overlay_data = base64.b64decode(overlay_before_b64)
            overlay_image = Image.open(io.BytesIO(overlay_data))
            print(f"DEBUG: Before overlay image size: {overlay_image.size}, mode: {overlay_image.mode}")
            
            temp_path = f'/tmp/before_{datetime.now().timestamp()}.png'
            overlay_image.save(temp_path, 'PNG')
            print(f"DEBUG: Before image saved to {temp_path}")
            
            pdf.image(temp_path, x=10, y=pdf.get_y(), w=190)
            print(f"DEBUG: Before image added to PDF")
            
        except Exception as e:
            print(f"DEBUG: Exception in before image processing: {e}")
            import traceback
            traceback.print_exc()
    
    if overlay_after_b64:
        try:
            pdf.add_page()
            pdf.chapter_title('ANALIZA DUPA INCIDENT')
            
            incident_date = analysis_data.get('incident_date', 'N/A')
            after_date = analysis_data.get('after_date', 'N/A')
            
            pdf.set_font('Times', 'B', 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, normalize_romanian_text(f'Perioada: {incident_date} - {after_date}'), 0, 1, 'L')
            pdf.ln(5)
            
            damage_percent = analysis_data.get('damage_percent', 0)
            pdf.section_text('Procent Deteriorare:', f'{damage_percent:.2f}%', bold_value=True)
            pdf.section_text('Zona Afectata:', f'{analysis_data.get("damaged_area_ha", 0):.2f} ha', bold_value=True)
            if analysis_data.get('ndvi_after'):
                pdf.section_text('NDVI Mediu:', f'{analysis_data.get("ndvi_after"):.3f}')
            pdf.ln(10)
            
            print(f"DEBUG: Processing after overlay")
            overlay_data = base64.b64decode(overlay_after_b64)
            overlay_image = Image.open(io.BytesIO(overlay_data))
            print(f"DEBUG: After overlay image size: {overlay_image.size}, mode: {overlay_image.mode}")
            
            temp_path = f'/tmp/after_{datetime.now().timestamp()}.png'
            overlay_image.save(temp_path, 'PNG')
            print(f"DEBUG: After image saved to {temp_path}")
            
            pdf.image(temp_path, x=10, y=pdf.get_y(), w=190)
            print(f"DEBUG: After image added to PDF")
            
        except Exception as e:
            print(f"DEBUG: Exception in after image processing: {e}")
            import traceback
            traceback.print_exc()
            print(f"Failed to add satellite images to PDF: {e}")
    
    if ai_insights:
        pdf.add_page()
        pdf.chapter_title('ANALIZA DETALIATA AI')
        parse_markdown_to_pdf(pdf, ai_insights)
        pdf.ln(8)
    
    pdf.add_page()
    pdf.chapter_title('CONCLUZII SI RECOMANDARI')
    
    pdf.set_font('Times', '', 9)
    conclusion = f"""Acest raport a fost generat automat folosind tehnologia de analiza satelitara SpotyFire, 
bazata pe imagini Sentinel-1 SAR (Synthetic Aperture Radar) de la Agentia Spatiala Europeana.

Analiza comparativa a fost realizata pe doua perioade distincte:
- Perioada pre-incident: de la {analysis_data.get('before_date')} pana la {analysis_data.get('incident_date')}
- Perioada post-incident: de la {analysis_data.get('incident_date')} pana la {analysis_data.get('after_date')} (prezent)

Conform datelor satelitare, s-a identificat o deteriorare de {damage_percent:.2f}% din suprafata totala, 
reprezentand {analysis_data.get("damaged_area_ha", 0):.2f} hectare afectate dintr-un total de 
{analysis_data.get("total_area_ha", 0):.2f} hectare.

Costul estimat al daunelor este de {analysis_data.get("estimated_cost", 0):,.0f} RON, calculat pe baza 
valorii declarate a culturii de {property_data.get('crop_type', 'N/A')}.

Acest document serveste drept suport tehnic pentru dosarul de asigurare si poate fi utilizat ca dovada 
obiectiva a daunelor suferite."""
    
    pdf.multi_cell(0, 5, normalize_romanian_text(conclusion))
    pdf.ln(8)
    
    pdf.set_font('Times', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 4, normalize_romanian_text("""Nota: Acest raport este generat automat pe baza analizei satelitare si are caracter informativ. 
Pentru evaluarea finala a daunelor si stabilirea despagubirii, va rugam sa contactati compania de asigurari 
si sa urmati procedurile standard de evaluare la fata locului."""))
    
    return bytes(pdf.output())
