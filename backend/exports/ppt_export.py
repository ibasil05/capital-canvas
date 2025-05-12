from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import io
from typing import Dict, List, Any
from datetime import datetime

# Slide Layouts (assuming standard layouts)
TITLE_SLIDE_LAYOUT = 0
TITLE_AND_CONTENT_LAYOUT = 1
SECTION_HEADER_LAYOUT = 2 
BLANK_LAYOUT = 5
CONTENT_WITH_CAPTION_LAYOUT = 7 # Example, might vary

# Common Styling
FONT_NAME = "Inter"
TITLE_FONT_SIZE = Pt(32)
SUBTITLE_FONT_SIZE = Pt(18)
BODY_FONT_SIZE = Pt(12)
SMALL_FONT_SIZE = Pt(10)
BLACK_COLOR = RGBColor(0, 0, 0)
GREY_COLOR = RGBColor(107, 111, 118) # #6B6F76 from PRD

def add_title_slide(prs, title_text, subtitle_text):
    slide_layout = prs.slide_layouts[TITLE_SLIDE_LAYOUT]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    if title: title.text = title_text
    
    subtitle = slide.placeholders[1] # Placeholder index for subtitle can vary
    if subtitle: subtitle.text = subtitle_text
    return slide

def add_content_slide(prs, title_text, layout_idx=TITLE_AND_CONTENT_LAYOUT):
    slide_layout = prs.slide_layouts[layout_idx]
    slide = prs.slides.add_slide(slide_layout)
    title_shape = slide.shapes.title
    if title_shape: title_shape.text = title_text
    # Return slide and the main content placeholder (index typically 1 for content layouts)
    content_placeholder = None
    for shape in slide.placeholders:
        if shape.placeholder_format.idx == 1 or shape.name.startswith("Content Placeholder") or shape.name.startswith("Text Placeholder"): # Common indices/names
            content_placeholder = shape
            break
    return slide, content_placeholder

async def generate_ppt_export(model_results_data: Dict[str, Any]) -> bytes:
    """
    Generates a PowerPoint presentation from model results data.
    FR-7: 10-slide PPT deck.
    """
    prs = Presentation()
    
    # --- Slide 1: Title Slide ---
    company_name = model_results_data.get("company_name", "N/A")
    ticker = model_results_data.get("ticker", "N/A")
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    add_title_slide(prs, 
                      f"{company_name} ({ticker})", 
                      f"Financial Model & Valuation Overview\n{current_date}"
                     )

    # --- Slide 2: Executive Summary ---
    slide2, content_placeholder2 = add_content_slide(prs, "Executive Summary")
    if content_placeholder2:
        tf = content_placeholder2.text_frame
        tf.clear()
        p = tf.add_paragraph()
        p.text = "Key Valuation Outcomes:"
        p.font.bold = True
        p.font.size = Pt(16)
        
        valuation_data = model_results_data.get("valuation", {})
        dcf_val = valuation_data.get("dcf_valuation", {})
        comps_val = valuation_data.get("trading_comps_valuation", {})
        lbo_val = valuation_data.get("lbo_analysis", {})

        p = tf.add_paragraph()
        p.text = f"  • DCF Implied Price: ${dcf_val.get('price_per_share', 'N/A'):.2f}"
        p.level = 1
        p = tf.add_paragraph()
        p.text = f"  • Comps Implied Price: ${comps_val.get('price_per_share', 'N/A'):.2f}"
        p.level = 1
        if lbo_val and lbo_val.get('implied_irr') is not None:
            p = tf.add_paragraph()
            p.text = f"  • LBO Implied IRR: {lbo_val.get('implied_irr', 0)*100:.1f}%"
            p.level = 1
        
        tf.add_paragraph().text = "\nKey Assumptions:"
        tf.paragraphs[-1].font.bold = True
        tf.paragraphs[-1].font.size = Pt(16)
        assumptions = model_results_data.get("assumptions", {})
        p = tf.add_paragraph()
        p.text = f"  • Discount Rate (WACC): {assumptions.get('discount_rate', 0)*100:.1f}%"
        p.level = 1
        p = tf.add_paragraph()
        p.text = f"  • Terminal Growth Rate: {assumptions.get('terminal_growth_rate', 0)*100:.1f}%"
        p.level = 1

    # --- Slide 3: Company Profile (Simplified) ---
    slide3, content_placeholder3 = add_content_slide(prs, "Company Overview")
    if content_placeholder3:
        tf = content_placeholder3.text_frame
        tf.clear()
        p = tf.add_paragraph()
        p.text = f"Ticker: {ticker}"
        p = tf.add_paragraph()
        # Company data passed to ThreeStatementModel has profile, use it if available
        # This data isn't directly in model_results_data, but was used to create it.
        # For a pure export function, it might be better to pass company_data as well.
        # Placeholder text if detailed profile isn't in model_results_data directly.
        p.text = f"Industry: {model_results_data.get('company_data',{}).get('profile',{}).get('sector', 'N/A')}"
        p = tf.add_paragraph()
        p.text = f"Description: [Placeholder for brief company description]"
 
    # --- Slide 4 & 5: Financial Summary (Placeholders) ---
    # These would ideally be tables. Table creation is more involved.
    add_content_slide(prs, "Historical Financial Summary")[0].notes_slide.notes_text_frame.text = "Table of key IS/BS/CF items for historical years."
    add_content_slide(prs, "Projected Financial Summary")[0].notes_slide.notes_text_frame.text = "Table of key IS/BS/CF items for forecast years."

    # --- Slide 6: DCF Analysis Summary (Placeholder) ---
    add_content_slide(prs, "DCF Analysis Summary")[0].notes_slide.notes_text_frame.text = "Key DCF inputs, outputs, and sensitivity analysis placeholder."

    # --- Slide 7: Trading Comparables Summary (Placeholder) ---
    add_content_slide(prs, "Trading Comparables Summary")[0].notes_slide.notes_text_frame.text = "Comps table, multiples, and resulting valuation placeholder."

    # --- Slide 8: LBO Analysis Summary (Placeholder) ---
    add_content_slide(prs, "LBO Analysis Summary")[0].notes_slide.notes_text_frame.text = "Key LBO assumptions, IRR, MoIC placeholder."

    # --- Slide 9: Capital Structure Heatmap (Placeholder) ---
    add_content_slide(prs, "Capital Structure / Rating Heatmap")[0].notes_slide.notes_text_frame.text = "Visualization of WACC/Equity IRR across leverage scenarios (heatmap placeholder)."

    # --- Slide 10: Disclaimer ---
    slide10, content_placeholder10 = add_content_slide(prs, "Disclaimer")
    if content_placeholder10:
        tf = content_placeholder10.text_frame
        tf.clear()
        p = tf.add_paragraph()
        p.text = "This presentation and the information contained herein are confidential and proprietary. For discussion purposes only. The analyses are based on publicly available information and certain assumptions, and are not a guarantee of future performance."
        p.font.size = Pt(10)

    ppt_file = io.BytesIO()
    prs.save(ppt_file)
    ppt_file.seek(0)
    return ppt_file.read() 