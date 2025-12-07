import io
import base64
from datetime import datetime
from fpdf import FPDF
from typing import Dict, Optional
import requests
from PIL import Image

class ReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(5, 150, 105)
        self.cell(0, 10, 'SpotyFire - Raport Analiza Satelit', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_satellite_report_pdf(
    property_name: str,
    analysis_data: Dict,
    property_data: Dict,
    overlay_b64: Optional[str] = None
) -> bytes:
    pdf = ReportPDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(30, 41, 59)
    pdf.cell(0, 10, f'Teren: {property_name}', 0, 1, 'L', True)
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, f'Data generarii: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1)
    pdf.cell(0, 6, f'Perioada analizata: {analysis_data.get("date_range_start")} - {analysis_data.get("date_range_end")}', 0, 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 252, 231)
    pdf.cell(0, 10, 'Date Teren', 0, 1, 'L', True)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 6, 'Tip cultura:', 0, 0)
    pdf.cell(0, 6, property_data.get('crop_type', 'N/A'), 0, 1)
    
    pdf.cell(60, 6, 'Suprafata totala:', 0, 0)
    pdf.cell(0, 6, f'{property_data.get("area_ha", 0):.2f} ha', 0, 1)
    
    pdf.cell(60, 6, 'Coordonate centru:', 0, 0)
    pdf.cell(0, 6, f'{property_data.get("center_lat"):.6f}, {property_data.get("center_lng"):.6f}', 0, 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(254, 226, 226)
    pdf.cell(0, 10, 'Rezultate Analiza Satelit', 0, 1, 'L', True)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 10)
    
    damage_percent = analysis_data.get('damage_percent', 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 6, 'Procent deteriorare:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(220, 38, 38)
    pdf.cell(0, 6, f'{damage_percent:.2f}%', 0, 1)
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 6, 'Zona afectata:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(234, 88, 12)
    pdf.cell(0, 6, f'{analysis_data.get("damaged_area_ha", 0):.2f} ha', 0, 1)
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 6, 'Cost estimat:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(202, 138, 4)
    pdf.cell(0, 6, f'{analysis_data.get("estimated_cost", 0):,.0f} RON', 0, 1)
    pdf.set_text_color(0, 0, 0)
    
    if analysis_data.get('ndvi_before') and analysis_data.get('ndvi_after'):
        pdf.ln(3)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 6, 'NDVI inainte:', 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f'{analysis_data.get("ndvi_before"):.3f}', 0, 1)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 6, 'NDVI dupa:', 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f'{analysis_data.get("ndvi_after"):.3f}', 0, 1)
    
    pdf.ln(5)
    
    if overlay_b64 and property_data.get('center_lat') and property_data.get('center_lng'):
        try:
            lat = property_data['center_lat']
            lng = property_data['center_lng']
            
            satellite_url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?bbox={lng-0.1},{lat-0.1},{lng+0.1},{lat+0.1}&size=800,600&format=png&f=image"
            
            sat_response = requests.get(satellite_url, timeout=10)
            if sat_response.status_code == 200:
                sat_image = Image.open(io.BytesIO(sat_response.content))
                
                overlay_data = base64.b64decode(overlay_b64)
                overlay_image = Image.open(io.BytesIO(overlay_data))
                
                overlay_image = overlay_image.resize(sat_image.size, Image.Resampling.LANCZOS)
                
                if overlay_image.mode != 'RGBA':
                    overlay_image = overlay_image.convert('RGBA')
                
                combined = Image.alpha_composite(
                    sat_image.convert('RGBA'),
                    overlay_image
                )
                
                temp_path = f'/tmp/satellite_overlay_{datetime.now().timestamp()}.png'
                combined.save(temp_path, 'PNG')
                
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, 'Harta Satelit cu Deteriorare', 0, 1, 'L')
                pdf.ln(2)
                
                pdf.image(temp_path, x=10, y=pdf.get_y(), w=190)
                pdf.ln(100)
            else:
                overlay_data = base64.b64decode(overlay_b64)
                overlay_image = Image.open(io.BytesIO(overlay_data))
                
                temp_path = f'/tmp/overlay_{datetime.now().timestamp()}.png'
                overlay_image.save(temp_path, 'PNG')
                
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, 'Harta Deteriorare', 0, 1, 'L')
                pdf.ln(2)
                
                pdf.image(temp_path, x=10, y=pdf.get_y(), w=190)
                pdf.ln(100)
            
        except Exception as e:
            print(f"Failed to add satellite/overlay image to PDF: {e}")
    
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 5, 
        'Acest raport este generat automat folosind analiza imaginilor satelitare Sentinel-1. '
        'Datele prezentate sunt estimari si pot varia in functie de conditiile meteorologice si de calitatea datelor.'
    )
    
    return bytes(pdf.output())
