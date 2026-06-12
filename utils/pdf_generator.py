import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_sales_pdf(invoice_data, file_path):
    """
    Generates a professional PDF invoice.
    invoice_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - invoice_number, date
      - customer_name, customer_mobile, customer_address, customer_gst
      - items: list of dicts {"name", "qty", "rate", "discount", "total"}
      - total_amount, paid_amount, balance
    """
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    style_shop_name = ParagraphStyle(
        'ShopName',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_header_label = ParagraphStyle(
        'HeaderLabel',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b')
    )
    
    style_header_val = ParagraphStyle(
        'HeaderVal',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1e293b')
    )

    style_title = ParagraphStyle(
        'InvoiceTitle',
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1e293b'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'Subtext',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldText',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Header Grid (Shop Details Left, Invoice Title & Info Right)
    left_info = [
        Paragraph(invoice_data['shop_name'], style_shop_name),
        Paragraph(invoice_data['shop_address'], style_sub),
        Paragraph(f"Contact: {invoice_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {invoice_data['shop_gst']}", style_sub)
    ]
    
    right_info = [
        Paragraph("TAX INVOICE", style_title),
        Spacer(1, 10),
        Paragraph(f"Invoice No: <b>{invoice_data['invoice_number']}</b>", style_bold),
        Paragraph(f"Date: {invoice_data['date']}", style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    # Page width is 612 - 72 = 540
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))

    # 2. Billing details (Bill To)
    bill_to_data = [
        [
            Paragraph("<b>BILL TO:</b>", style_bold), 
            Paragraph("", style_sub)
        ],
        [
            Paragraph(invoice_data['customer_name'], style_bold),
            Paragraph(f"Mobile: {invoice_data['customer_mobile']}", style_sub)
        ],
        [
            Paragraph(invoice_data['customer_address'] or "N/A", style_sub),
            Paragraph(f"Customer GST: {invoice_data['customer_gst'] or '-'}", style_sub)
        ]
    ]
    bill_to_table = Table(bill_to_data, colWidths=[270, 270])
    bill_to_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(bill_to_table)
    story.append(Spacer(1, 20))

    # 3. Items Table
    # Table Widths: Item Name (240), Qty (40), Rate (90), Discount (80), Total (90) = 540
    item_header_style = ParagraphStyle(
        'ItemHeader',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )
    
    table_data = [
        [
            Paragraph("Item Description", item_header_style),
            Paragraph("Qty", item_header_style),
            Paragraph("Rate (Rs.)", item_header_style),
            Paragraph("Discount (Rs.)", item_header_style),
            Paragraph("Total (Rs.)", item_header_style)
        ]
    ]

    for item in invoice_data['items']:
        table_data.append([
            Paragraph(item['name'], style_sub),
            Paragraph(str(item['qty']), style_sub),
            Paragraph(f"{item['rate']:,.2f}", style_sub),
            Paragraph(f"{item['discount']:,.2f}", style_sub),
            Paragraph(f"{item['total']:,.2f}", style_bold)
        ])

    items_table = Table(table_data, colWidths=[240, 40, 90, 80, 90])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e1b4b')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    # 4. Summary / Totals block
    summary_data = [
        [Paragraph("", style_sub), Paragraph("Grand Total:", style_bold), Paragraph(f"Rs. {invoice_data['total_amount']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Amount Paid:", style_bold), Paragraph(f"Rs. {invoice_data['paid_amount']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Balance Outstanding:", style_bold), Paragraph(f"Rs. {invoice_data['balance']:,.2f}", style_bold)]
    ]
    
    summary_table = Table(summary_data, colWidths=[300, 140, 100])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('LINEBELOW', (1,-1), (-1,-1), 1.5, colors.HexColor('#6366f1')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 40))

    # 5. Footer & Sign-off
    footer_text = "<b>Terms & Conditions:</b><br/>1. Goods once sold will not be taken back.<br/>2. Standard product warranty is backed by the respective manufacturer.<br/>3. Please bring this invoice for any service/warranty claims."
    story.append(Paragraph(footer_text, style_sub))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<font size=10 color='#6366f1'><b>Thank you for your business! Visit again.</b></font>", ParagraphStyle('CenterText', parent=style_sub, alignment=1)))

    doc.build(story)
