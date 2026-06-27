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


def generate_purchase_pdf(purchase_data, file_path):
    """
    Generates a professional PDF purchase bill.
    purchase_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - invoice_number, date
      - supplier_name, supplier_mobile, supplier_address
      - items: list of dicts {"name", "qty", "rate", "total"}
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
        'ShopNamePurchase',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_header_label = ParagraphStyle(
        'HeaderLabelPurchase',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b')
    )
    
    style_header_val = ParagraphStyle(
        'HeaderValPurchase',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1e293b')
    )

    style_title = ParagraphStyle(
        'InvoiceTitlePurchase',
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1e293b'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextPurchase',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextPurchase',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Header Grid (Shop Details Left, Invoice Title & Info Right)
    left_info = [
        Paragraph(purchase_data['shop_name'], style_shop_name),
        Paragraph(purchase_data['shop_address'], style_sub),
        Paragraph(f"Contact: {purchase_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {purchase_data['shop_gst']}", style_sub)
    ]
    
    right_info = [
        Paragraph("PURCHASE BILL", style_title),
        Spacer(1, 10),
        Paragraph(f"Invoice No: <b>{purchase_data['invoice_number']}</b>", style_bold),
        Paragraph(f"Date: {purchase_data['date']}", style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))

    # 2. Supplier details (Bill From)
    bill_from_data = [
        [
            Paragraph("<b>BILL FROM (SUPPLIER):</b>", style_bold), 
            Paragraph("", style_sub)
        ],
        [
            Paragraph(purchase_data['supplier_name'], style_bold),
            Paragraph(f"Mobile: {purchase_data['supplier_mobile']}", style_sub)
        ],
        [
            Paragraph(purchase_data['supplier_address'] or "N/A", style_sub),
            Paragraph("", style_sub)
        ]
    ]
    bill_from_table = Table(bill_from_data, colWidths=[270, 270])
    bill_from_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(bill_from_table)
    story.append(Spacer(1, 20))

    # 3. Items Table
    # Table Widths: Item Description (320), Qty (50), Rate (80), Total (90) = 540
    item_header_style = ParagraphStyle(
        'ItemHeaderPurchase',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )
    
    table_data = [
        [
            Paragraph("Item Description", item_header_style),
            Paragraph("Qty", item_header_style),
            Paragraph("Rate (Rs.)", item_header_style),
            Paragraph("Total (Rs.)", item_header_style)
        ]
    ]

    for item in purchase_data['items']:
        table_data.append([
            Paragraph(item['name'], style_sub),
            Paragraph(str(item['qty']), style_sub),
            Paragraph(f"{item['rate']:,.2f}", style_sub),
            Paragraph(f"{item['total']:,.2f}", style_bold)
        ])

    items_table = Table(table_data, colWidths=[320, 50, 80, 90])
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
        [Paragraph("", style_sub), Paragraph("Grand Total:", style_bold), Paragraph(f"Rs. {purchase_data['total_amount']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Amount Paid:", style_bold), Paragraph(f"Rs. {purchase_data['paid_amount']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Balance Payable:", style_bold), Paragraph(f"Rs. {purchase_data['balance']:,.2f}", style_bold)]
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
    footer_text = "<b>Terms & Conditions:</b><br/>1. Goods received in good condition.<br/>2. All disputes subject to local jurisdiction."
    story.append(Paragraph(footer_text, style_sub))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<font size=10 color='#6366f1'><b>Thank you!</b></font>", ParagraphStyle('CenterTextPurchase', parent=style_sub, alignment=1)))

    doc.build(story)


def generate_service_pdf(service_data, file_path):
    """
    Generates a professional PDF service invoice.
    service_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - job_number, date
      - customer_name, customer_mobile
      - device_model, imei, complaint, status, technician
      - service_charge
      - parts: list of dicts {"name", "qty", "cost", "total"}
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
        'ShopNameService',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_header_label = ParagraphStyle(
        'HeaderLabelService',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b')
    )
    
    style_header_val = ParagraphStyle(
        'HeaderValService',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1e293b')
    )

    style_title = ParagraphStyle(
        'InvoiceTitleService',
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1e293b'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextService',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextService',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Header Grid (Shop Details Left, Invoice Title & Info Right)
    left_info = [
        Paragraph(service_data['shop_name'], style_shop_name),
        Paragraph(service_data['shop_address'], style_sub),
        Paragraph(f"Contact: {service_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {service_data['shop_gst']}", style_sub)
    ]
    
    right_info = [
        Paragraph("SERVICE INVOICE", style_title),
        Spacer(1, 10),
        Paragraph(f"Job Number: <b>{service_data['job_number']}</b>", style_bold),
        Paragraph(f"Date: {service_data['date']}", style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 15))

    # 2. Customer & Device details
    details_data = [
        [
            Paragraph("<b>CUSTOMER DETAILS:</b>", style_bold), 
            Paragraph("<b>DEVICE DETAILS:</b>", style_bold)
        ],
        [
            Paragraph(f"Name: {service_data['customer_name']}", style_sub),
            Paragraph(f"Model: {service_data['device_model']}", style_sub)
        ],
        [
            Paragraph(f"Mobile: {service_data['customer_mobile']}", style_sub),
            Paragraph(f"IMEI/Serial: {service_data['imei']}", style_sub)
        ],
        [
            Paragraph("", style_sub),
            Paragraph(f"Technician: {service_data['technician'] or '-'}", style_sub)
        ],
        [
            Paragraph("", style_sub),
            Paragraph(f"Complaint: {service_data['complaint'] or '-'}", style_sub)
        ]
    ]
    details_table = Table(details_data, colWidths=[270, 270])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(details_table)
    story.append(Spacer(1, 15))

    # 3. Items Table (Labor + Spare Parts)
    item_header_style = ParagraphStyle(
        'ItemHeaderService',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )
    
    table_data = [
        [
            Paragraph("Service / Part Description", item_header_style),
            Paragraph("Qty", item_header_style),
            Paragraph("Rate (Rs.)", item_header_style),
            Paragraph("Total (Rs.)", item_header_style)
        ]
    ]

    # Add labor
    table_data.append([
        Paragraph("Service Labor & Diagnostic Charges", style_sub),
        Paragraph("1", style_sub),
        Paragraph(f"{service_data['service_charge']:,.2f}", style_sub),
        Paragraph(f"{service_data['service_charge']:,.2f}", style_bold)
    ])

    # Add spare parts
    for item in service_data['parts']:
        table_data.append([
            Paragraph(item['name'], style_sub),
            Paragraph(str(item['qty']), style_sub),
            Paragraph(f"{item['cost']:,.2f}", style_sub),
            Paragraph(f"{item['total']:,.2f}", style_bold)
        ])

    items_table = Table(table_data, colWidths=[320, 50, 80, 90])
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
        [Paragraph("", style_sub), Paragraph("Grand Total:", style_bold), Paragraph(f"Rs. {service_data['total_amount']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Amount Paid:", style_bold), Paragraph(f"Rs. {service_data['paid_amount']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Balance Due:", style_bold), Paragraph(f"Rs. {service_data['balance']:,.2f}", style_bold)]
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
    story.append(Spacer(1, 30))

    # 5. Footer & Sign-off
    footer_text = "<b>Terms & Conditions:</b><br/>1. 30 days warranty on spare parts replaced (does not cover physical/liquid damage).<br/>2. Please collect device within 15 days of repair completion."
    story.append(Paragraph(footer_text, style_sub))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<font size=10 color='#6366f1'><b>Thank you! Visit again.</b></font>", ParagraphStyle('CenterTextService', parent=style_sub, alignment=1)))

    doc.build(story)


def generate_payment_pdf(payment_data, file_path):
    """
    Generates a professional PDF payment receipt / voucher.
    payment_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - payment_id, date, party_type (customer/supplier), party_name, party_mobile
      - amount, payment_mode, remarks
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
        'ShopNamePayment',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_title = ParagraphStyle(
        'InvoiceTitlePayment',
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1e293b'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextPayment',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextPayment',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Header Grid (Shop Details Left, Receipt Title & Info Right)
    left_info = [
        Paragraph(payment_data['shop_name'], style_shop_name),
        Paragraph(payment_data['shop_address'], style_sub),
        Paragraph(f"Contact: {payment_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {payment_data['shop_gst']}", style_sub)
    ]
    
    title_text = "PAYMENT RECEIPT" if payment_data['party_type'] == 'customer' else "PAYMENT VOUCHER"
    right_info = [
        Paragraph(title_text, style_title),
        Spacer(1, 10),
        Paragraph(f"Receipt No: <b>#{payment_data['payment_id']}</b>", style_bold),
        Paragraph(f"Date: {payment_data['date']}", style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 25))

    # 2. Receipt Details Card
    party_label = "RECEIVED FROM:" if payment_data['party_type'] == 'customer' else "PAID TO:"
    
    payment_details = [
        [
            Paragraph(f"<b>{party_label}</b>", style_bold),
            Paragraph(f"<b>{payment_data['party_name']}</b> (Mobile: {payment_data['party_mobile']})", style_sub)
        ],
        [
            Paragraph("<b>AMOUNT:</b>", style_bold),
            Paragraph(f"<b>Rs. {payment_data['amount']:,.2f}</b>", style_bold)
        ],
        [
            Paragraph("<b>PAYMENT MODE:</b>", style_bold),
            Paragraph(payment_data['payment_mode'], style_sub)
        ],
        [
            Paragraph("<b>REMARKS / NOTES:</b>", style_bold),
            Paragraph(payment_data['remarks'] or "-", style_sub)
        ]
    ]
    
    details_table = Table(payment_details, colWidths=[150, 390])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(details_table)
    story.append(Spacer(1, 50))

    # 3. Signatures
    sig_data = [
        [
            Paragraph("Customer/Receiver Signature", style_sub),
            Paragraph("Authorized Signatory", style_sub)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#475569')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))
    
    story.append(sig_table)

    doc.build(story)


def generate_ledger_pdf(ledger_data, file_path):
    """
    Generates a professional PDF ledger breakup report.
    ledger_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - date  (Statement Date / Date Generated)
      - party_type ('customer' or 'supplier')
      - party_name, party_mobile, party_address
      - transactions: list of dicts {"date", "ref", "desc", "debit", "credit", "balance"}
      - net_balance, balance_label
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
        'ShopNameLedger',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_title = ParagraphStyle(
        'LedgerTitle',
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1e293b'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextLedger',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextLedger',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )
    
    style_red = ParagraphStyle(
        'RedTextLedger',
        parent=style_sub,
        textColor=colors.HexColor('#ef4444')
    )
    
    style_green = ParagraphStyle(
        'GreenTextLedger',
        parent=style_sub,
        textColor=colors.HexColor('#10b981')
    )

    story = []

    # 1. Header Grid (Shop Details Left, Title & Statement Date Right)
    left_info = [
        Paragraph(ledger_data['shop_name'], style_shop_name),
        Paragraph(ledger_data['shop_address'], style_sub),
        Paragraph(f"Contact: {ledger_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {ledger_data['shop_gst']}", style_sub)
    ]
    
    right_info = [
        Paragraph("LEDGER STATEMENT", style_title),
        Spacer(1, 10),
        Paragraph(f"Generated Date: {ledger_data['date']}", style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))

    # 2. Party details
    party_hdr = "CUSTOMER DETAILS" if ledger_data['party_type'] == 'customer' else "SUPPLIER DETAILS"
    party_data = [
        [
            Paragraph(f"<b>{party_hdr}:</b>", style_bold), 
            Paragraph("", style_sub)
        ],
        [
            Paragraph(ledger_data['party_name'], style_bold),
            Paragraph(f"Mobile: {ledger_data['party_mobile']}", style_sub)
        ],
        [
            Paragraph(ledger_data['party_address'] or "N/A", style_sub),
            Paragraph("", style_sub)
        ]
    ]
    party_table = Table(party_data, colWidths=[270, 270])
    party_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(party_table)
    story.append(Spacer(1, 20))

    # 3. Transactions Table
    # Table Widths: Date (70), Ref / Invoice (90), Description (160), Debit (75), Credit (75), Balance (70) = 540
    item_header_style = ParagraphStyle(
        'ItemHeaderLedger',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )
    
    headers = [
        Paragraph("Date", item_header_style),
        Paragraph("Ref / Invoice", item_header_style),
        Paragraph("Description", item_header_style),
        Paragraph("Debit (+)" if ledger_data['party_type'] == 'customer' else "Debit (-)", item_header_style),
        Paragraph("Credit (-)" if ledger_data['party_type'] == 'customer' else "Credit (+)", item_header_style),
        Paragraph("Balance", item_header_style)
    ]

    table_data = [headers]

    for tx in ledger_data['transactions']:
        # debit formatting
        if tx['debit'] > 0:
            debit_val = f"{tx['debit']:,.2f}"
            debit_p = Paragraph(debit_val, style_red if ledger_data['party_type'] == 'customer' else style_green)
        else:
            debit_p = Paragraph("-", style_sub)
            
        # credit formatting
        if tx['credit'] > 0:
            credit_val = f"{tx['credit']:,.2f}"
            credit_p = Paragraph(credit_val, style_green if ledger_data['party_type'] == 'customer' else style_red)
        else:
            credit_p = Paragraph("-", style_sub)
            
        # balance formatting
        bal_val = f"{tx['balance']:,.2f}"
        
        table_data.append([
            Paragraph(tx['date'], style_sub),
            Paragraph(tx['ref'], style_sub),
            Paragraph(tx['desc'], style_sub),
            debit_p,
            credit_p,
            Paragraph(bal_val, style_bold)
        ])

    tx_table = Table(table_data, colWidths=[70, 90, 160, 75, 75, 70])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e1b4b')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(tx_table)
    story.append(Spacer(1, 15))

    # 4. Summary / Outstanding
    summary_data = [
        [Paragraph("", style_sub), Paragraph(f"{ledger_data['balance_label']}:", style_bold), Paragraph(f"Rs. {ledger_data['net_balance']:,.2f}", style_bold)]
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
    story.append(Paragraph("<font size=10 color='#6366f1'><b>Thank you!</b></font>", ParagraphStyle('CenterTextLedger', parent=style_sub, alignment=1)))

    doc.build(story)

def generate_money_transfer_pdf(transfer_data, file_path):
    """
    Generates a professional PDF money transfer receipt / voucher.
    transfer_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - transaction_number, date
      - customer_name, beneficiary_name
      - transfer_type ('UPI' or 'Bank Transfer')
      - upi_id (if UPI)
      - bank_account_number, ifsc_code (if Bank Transfer)
      - amount, service_charge, total_amount
      - deadline_date, status, remarks
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
    
    style_shop_name = ParagraphStyle(
        'ShopNameMT',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_title = ParagraphStyle(
        'InvoiceTitleMT',
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1e293b'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextMT',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextMT',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Header Grid (Shop Details Left, Title & Info Right)
    left_info = [
        Paragraph(transfer_data['shop_name'], style_shop_name),
        Paragraph(transfer_data['shop_address'], style_sub),
        Paragraph(f"Contact: {transfer_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {transfer_data['shop_gst']}", style_sub)
    ]
    
    right_info = [
        Paragraph("MONEY TRANSFER RECEIPT", style_title),
        Spacer(1, 10),
        Paragraph(f"Transaction No: <b>{transfer_data['transaction_number']}</b>", style_bold),
        Paragraph(f"Date: {transfer_data['date']}", style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 25))

    # 2. Receipt Details Card
    details = [
        [
            Paragraph("<b>SENDER (CUSTOMER):</b>", style_bold),
            Paragraph(transfer_data['customer_name'], style_sub)
        ],
        [
            Paragraph("<b>BENEFICIARY NAME:</b>", style_bold),
            Paragraph(transfer_data['beneficiary_name'], style_sub)
        ],
        [
            Paragraph("<b>TRANSFER TYPE:</b>", style_bold),
            Paragraph(transfer_data['transfer_type'], style_sub)
        ]
    ]

    if transfer_data['transfer_type'] == 'UPI':
        details.append([
            Paragraph("<b>UPI ID / MOBILE:</b>", style_bold),
            Paragraph(transfer_data['upi_id'] or "-", style_sub)
        ])
    else:
        details.append([
            Paragraph("<b>BANK ACCOUNT NO:</b>", style_bold),
            Paragraph(transfer_data['bank_account_number'] or "-", style_sub)
        ])
        details.append([
            Paragraph("<b>IFSC CODE:</b>", style_bold),
            Paragraph(transfer_data['ifsc_code'] or "-", style_sub)
        ])

    details.extend([
        [
            Paragraph("<b>TRANSFER AMOUNT:</b>", style_bold),
            Paragraph(f"Rs. {transfer_data['amount']:,.2f}", style_bold)
        ],
        [
            Paragraph("<b>SERVICE CHARGE:</b>", style_bold),
            Paragraph(f"Rs. {transfer_data['service_charge']:,.2f}", style_sub)
        ],
        [
            Paragraph("<b>TOTAL PAYABLE:</b>", style_bold),
            Paragraph(f"Rs. {transfer_data['total_amount']:,.2f}", style_bold)
        ],
        [
            Paragraph("<b>DEADLINE DATE:</b>", style_bold),
            Paragraph(transfer_data['deadline_date'], style_sub)
        ],
        [
            Paragraph("<b>STATUS:</b>", style_bold),
            Paragraph(transfer_data['status'], style_bold)
        ],
        [
            Paragraph("<b>REMARKS / NOTES:</b>", style_bold),
            Paragraph(transfer_data['remarks'] or "-", style_sub)
        ]
    ])
    
    details_table = Table(details, colWidths=[150, 390])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#cbd5e1')),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#6366f1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(details_table)
    story.append(Spacer(1, 40))

    # 3. Signatures
    sig_data = [
        [
            Paragraph("Customer Signature", style_sub),
            Paragraph("Authorized Signatory", style_sub)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    story.append(sig_table)
    doc.build(story)


def generate_low_stock_pdf(report_data, file_path):
    """
    Generates a professional PDF report for Low Stock items.
    report_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - date
      - items: list of dicts {"name", "brand_model", "current_stock", "low_limit"}
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
    
    style_shop_name = ParagraphStyle(
        'ShopNameStock',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_title = ParagraphStyle(
        'StockTitle',
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1e293b'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextStock',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextStock',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Header Grid
    left_info = [
        Paragraph(report_data['shop_name'], style_shop_name),
        Paragraph(report_data['shop_address'], style_sub),
        Paragraph(f"Contact: {report_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {report_data['shop_gst']}", style_sub)
    ]
    
    right_info = [
        Paragraph("LOW STOCK REPORT", style_title),
        Spacer(1, 10),
        Paragraph(f"Date Generated: {report_data['date']}", style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))

    # 2. Divider line
    story.append(Table([[""]], colWidths=[540], rowHeights=[1], style=TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#6366f1')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ])))
    story.append(Spacer(1, 15))

    # 3. Items Table
    table_data = [
        [
            Paragraph("Product Name", style_bold),
            Paragraph("Brand / Model", style_bold),
            Paragraph("Current Stock", style_bold),
            Paragraph("Low Limit", style_bold)
        ]
    ]

    for item in report_data['items']:
        stock_qty = item['current_stock']
        table_data.append([
            Paragraph(item['name'], style_sub),
            Paragraph(item['brand_model'], style_sub),
            Paragraph(str(stock_qty), style_bold),
            Paragraph(str(item['low_limit']), style_sub)
        ])

    items_table = Table(table_data, colWidths=[240, 160, 70, 70])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 30))

    # 4. Footer & Sign-off
    story.append(Paragraph("<font size=10 color='#6366f1'><b>SUN COMPUTERS Stock Management System</b></font>", ParagraphStyle('CenterTextStockFooter', parent=style_sub, alignment=1)))

    doc.build(story)


def generate_outstanding_pdf(report_data, file_path):
    """
    Generates a professional PDF report for Outstanding Balances (Customer Receivables or Supplier Payables).
    report_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - date
      - party_type: 'customer' or 'supplier'
      - items: list of dicts {"name", "mobile", "balance"}
      - total_amount
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
    
    style_shop_name = ParagraphStyle(
        'ShopNameOutstanding',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    title_text = "CUSTOMER OUTSTANDING BALANCES" if report_data['party_type'] == 'customer' else "SUPPLIER OUTSTANDING BALANCES"
    title_color = '#f59e0b' if report_data['party_type'] == 'customer' else '#ef4444'
    
    style_title = ParagraphStyle(
        'OutstandingTitle',
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor(title_color),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextOutstanding',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextOutstanding',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Header Grid
    left_info = [
        Paragraph(report_data['shop_name'], style_shop_name),
        Paragraph(report_data['shop_address'], style_sub),
        Paragraph(f"Contact: {report_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {report_data['shop_gst']}", style_sub)
    ]
    
    right_info = [
        Paragraph(title_text, style_title),
        Spacer(1, 10),
        Paragraph(f"Date Generated: {report_data['date']}", style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))

    # 2. Divider line
    story.append(Table([[""]], colWidths=[540], rowHeights=[1], style=TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor(title_color)),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ])))
    story.append(Spacer(1, 15))

    # 3. Items Table
    headers = [
        Paragraph("Customer Name" if report_data['party_type'] == 'customer' else "Supplier Name", style_bold),
        Paragraph("Mobile / Contact", style_bold),
        Paragraph("Outstanding Balance (Rs.)" if report_data['party_type'] == 'customer' else "Payable Balance (Rs.)", style_bold)
    ]
    table_data = [headers]

    for item in report_data['items']:
        table_data.append([
            Paragraph(item['name'], style_sub),
            Paragraph(item['mobile'], style_sub),
            Paragraph(f"Rs. {item['balance']:,.2f}", style_bold)
        ])

    # Add Total Row
    table_data.append([
        Paragraph("<b>TOTAL</b>", style_bold),
        Paragraph("", style_sub),
        Paragraph(f"<b>Rs. {report_data['total_amount']:,.2f}</b>", style_bold)
    ])

    items_table = Table(table_data, colWidths=[240, 160, 140])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f1f5f9')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,1), (-1,-2), 0.5, colors.HexColor('#e2e8f0')),
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor('#94a3b8')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 30))

    # 4. Footer & Sign-off
    story.append(Paragraph("<font size=10 color='#6366f1'><b>SUN COMPUTERS Management System</b></font>", ParagraphStyle('CenterTextFooter', parent=style_sub, alignment=1)))

    doc.build(story)


def generate_sales_return_pdf(return_data, file_path):
    """
    Generates a professional PDF credit note for sales return.
    return_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - return_number, date, invoice_number (optional original invoice)
      - customer_name, customer_mobile, customer_address
      - items: list of dicts {"name", "qty", "rate", "total"}
      - total_amount, refund_amount, balance_deducted
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
    
    style_shop_name = ParagraphStyle(
        'ShopNameSR',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_title = ParagraphStyle(
        'SRTitle',
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#dc2626'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextSR',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextSR',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Header Grid (Shop Details Left, Title & Info Right)
    left_info = [
        Paragraph(return_data['shop_name'], style_shop_name),
        Paragraph(return_data['shop_address'], style_sub),
        Paragraph(f"Contact: {return_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {return_data['shop_gst']}", style_sub)
    ]
    
    ref_invoice = return_data.get('invoice_number')
    ref_invoice_str = f"Ref Invoice: {ref_invoice}" if ref_invoice else ""
    
    right_info = [
        Paragraph("CREDIT NOTE", style_title),
        Paragraph("(SALES RETURN)", ParagraphStyle('SRSubTitle', parent=style_bold, alignment=2, textColor=colors.HexColor('#64748b'))),
        Spacer(1, 5),
        Paragraph(f"Return No: <b>{return_data['return_number']}</b>", style_bold),
        Paragraph(f"Date: {return_data['date']}", style_sub),
        Paragraph(ref_invoice_str, style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))

    # 2. Customer details (Bill To)
    bill_to_data = [
        [
            Paragraph("<b>CUSTOMER DETAILS:</b>", style_bold), 
            Paragraph("", style_sub)
        ],
        [
            Paragraph(return_data['customer_name'], style_bold),
            Paragraph(f"Mobile: {return_data['customer_mobile']}", style_sub)
        ],
        [
            Paragraph(return_data['customer_address'] or "N/A", style_sub),
            Paragraph("", style_sub)
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
    item_header_style = ParagraphStyle(
        'ItemHeaderSR',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )
    
    table_data = [
        [
            Paragraph("Returned Item Description", item_header_style),
            Paragraph("Qty", item_header_style),
            Paragraph("Rate (Rs.)", item_header_style),
            Paragraph("Total (Rs.)", item_header_style)
        ]
    ]

    for item in return_data['items']:
        table_data.append([
            Paragraph(item['name'], style_sub),
            Paragraph(str(item['qty']), style_sub),
            Paragraph(f"{item['rate']:,.2f}", style_sub),
            Paragraph(f"{item['total']:,.2f}", style_bold)
        ])

    items_table = Table(table_data, colWidths=[320, 50, 80, 90])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7f1d1d')), # Dark red header
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
        [Paragraph("", style_sub), Paragraph("Total Return Value:", style_bold), Paragraph(f"Rs. {return_data['total_amount']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Refund Paid (Cash/Bank):", style_bold), Paragraph(f"Rs. {return_data['refund_amount']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Balance Adjusted:", style_bold), Paragraph(f"Rs. {return_data['balance_deducted']:,.2f}", style_bold)]
    ]
    
    summary_table = Table(summary_data, colWidths=[300, 140, 100])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('LINEBELOW', (1,-1), (-1,-1), 1.5, colors.HexColor('#dc2626')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 40))

    # 5. Footer & Sign-off
    story.append(Paragraph("This is a Credit Note issued against a sales return.", style_sub))
    doc.build(story)


def generate_purchase_return_pdf(return_data, file_path):
    """
    Generates a professional PDF debit note for purchase return.
    return_data keys:
      - shop_name, shop_contact, shop_address, shop_gst
      - return_number, date, invoice_number (optional original invoice)
      - supplier_name, supplier_mobile, supplier_address
      - items: list of dicts {"name", "qty", "rate", "total"}
      - total_amount, refund_received, balance_deducted
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
    
    style_shop_name = ParagraphStyle(
        'ShopNamePR',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_title = ParagraphStyle(
        'PRTitle',
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#dc2626'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextPR',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextPR',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Header Grid (Shop Details Left, Title & Info Right)
    left_info = [
        Paragraph(return_data['shop_name'], style_shop_name),
        Paragraph(return_data['shop_address'], style_sub),
        Paragraph(f"Contact: {return_data['shop_contact']}", style_sub),
        Paragraph(f"GSTIN: {return_data['shop_gst']}", style_sub)
    ]
    
    ref_invoice = return_data.get('invoice_number')
    ref_invoice_str = f"Ref Invoice: {ref_invoice}" if ref_invoice else ""
    
    right_info = [
        Paragraph("DEBIT NOTE", style_title),
        Paragraph("(PURCHASE RETURN)", ParagraphStyle('PRSubTitle', parent=style_bold, alignment=2, textColor=colors.HexColor('#64748b'))),
        Spacer(1, 5),
        Paragraph(f"Return No: <b>{return_data['return_number']}</b>", style_bold),
        Paragraph(f"Date: {return_data['date']}", style_sub),
        Paragraph(ref_invoice_str, style_sub)
    ]
    
    header_table_data = [
        [left_info, right_info]
    ]
    
    header_table = Table(header_table_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))

    # 2. Supplier details (Bill To)
    bill_to_data = [
        [
            Paragraph("<b>SUPPLIER DETAILS:</b>", style_bold), 
            Paragraph("", style_sub)
        ],
        [
            Paragraph(return_data['supplier_name'], style_bold),
            Paragraph(f"Mobile: {return_data['supplier_mobile']}", style_sub)
        ],
        [
            Paragraph(return_data['supplier_address'] or "N/A", style_sub),
            Paragraph("", style_sub)
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
    item_header_style = ParagraphStyle(
        'ItemHeaderPR',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )
    
    table_data = [
        [
            Paragraph("Returned Item Description", item_header_style),
            Paragraph("Qty", item_header_style),
            Paragraph("Rate (Rs.)", item_header_style),
            Paragraph("Total (Rs.)", item_header_style)
        ]
    ]

    for item in return_data['items']:
        table_data.append([
            Paragraph(item['name'], style_sub),
            Paragraph(str(item['qty']), style_sub),
            Paragraph(f"{item['rate']:,.2f}", style_sub),
            Paragraph(f"{item['total']:,.2f}", style_bold)
        ])

    items_table = Table(table_data, colWidths=[320, 50, 80, 90])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7f1d1d')),
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
        [Paragraph("", style_sub), Paragraph("Total Return Value:", style_bold), Paragraph(f"Rs. {return_data['total_amount']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Refund Received (Cash/Bank):", style_bold), Paragraph(f"Rs. {return_data['refund_received']:,.2f}", style_bold)],
        [Paragraph("", style_sub), Paragraph("Balance Adjusted:", style_bold), Paragraph(f"Rs. {return_data['balance_deducted']:,.2f}", style_bold)]
    ]
    
    summary_table = Table(summary_data, colWidths=[300, 140, 100])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('LINEBELOW', (1,-1), (-1,-1), 1.5, colors.HexColor('#dc2626')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 40))

    # 5. Footer & Sign-off
    story.append(Paragraph("This is a Debit Note issued against a purchase return.", style_sub))
    doc.build(story)


def generate_inventory_profit_pdf(report_data, file_path):
    """
    Generates a professional A4 Landscape PDF report for Inventory holding and profitability.
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    import datetime

    # A4 Landscape is 841.89 x 595.27 points
    doc = SimpleDocTemplate(
        file_path,
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    style_shop_name = ParagraphStyle(
        'ShopNamePL',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#6366f1')
    )
    
    style_title = ParagraphStyle(
        'ReportTitlePL',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b'),
        alignment=2 # Right aligned
    )

    style_sub = ParagraphStyle(
        'SubtextPL',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    
    style_bold = ParagraphStyle(
        'BoldTextPL',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b')
    )

    style_header = ParagraphStyle(
        'HeaderStylePL',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    style_cell = ParagraphStyle(
        'CellStylePL',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )

    style_cell_bold = ParagraphStyle(
        'CellBoldStylePL',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )

    story = []
    
    # 1. Company and Report Header
    header_data = [
        [
            Paragraph(f"<b>{report_data['shop_name']}</b><br/>"
                      f"<font size=8>{report_data['shop_address']}<br/>"
                      f"Contact: {report_data['shop_contact']} | GSTIN: {report_data['shop_gst']}</font>", style_sub),
            Paragraph("<b>INVENTORY PROFITABILITY</b><br/>"
                      f"<font size=10>Date: {report_data['date']}<br/>"
                      f"Range: {report_data['date_range']}</font>", style_title)
        ]
    ]
    header_table = Table(header_data, colWidths=[400, 370])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    # 2. KPI Summary Section (6 horizontal boxes)
    kpi_card_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ])
    
    kpi_data = [
        [
            Paragraph("<font size=8 color='#64748b'>TOTAL PURCHASE VALUE</font><br/><b><font size=11 color='#1e293b'>Rs. " + f"{report_data['total_purchase_value']:,.2f}" + "</font></b>", style_sub),
            Paragraph("<font size=8 color='#64748b'>TOTAL SALES VALUE</font><br/><b><font size=11 color='#1e293b'>Rs. " + f"{report_data['total_sales_value']:,.2f}" + "</font></b>", style_sub),
            Paragraph("<font size=8 color='#64748b'>TOTAL GROSS PROFIT</font><br/><b><font size=11 color='#10b981'>Rs. " + f"{report_data['total_gross_profit']:,.2f}" + "</font></b>", style_sub),
            Paragraph("<font size=8 color='#64748b'>TOTAL INTEREST COST</font><br/><b><font size=11 color='#ef4444'>Rs. " + f"{report_data['total_interest_cost']:,.2f}" + "</font></b>", style_sub),
            Paragraph("<font size=8 color='#64748b'>TOTAL NET PROFIT</font><br/><b><font size=11 color='#6366f1'>Rs. " + f"{report_data['total_net_profit']:,.2f}" + "</font></b>", style_sub),
            Paragraph("<font size=8 color='#64748b'>AVG DAYS IN STOCK</font><br/><b><font size=11 color='#3b82f6'>" + f"{report_data['avg_days']:.1f}" + " Days</font></b>", style_sub),
        ]
    ]
    
    # 770pt width
    kpi_table = Table(kpi_data, colWidths=[128, 128, 129, 128, 129, 128])
    kpi_table.setStyle(kpi_card_style)
    story.append(kpi_table)
    story.append(Spacer(1, 15))
    
    # 3. Detailed Data Table
    table_headers = [
        Paragraph("Code", style_header),
        Paragraph("Product Name", style_header),
        Paragraph("Pur. Date", style_header),
        Paragraph("Sale Date", style_header),
        Paragraph("Days", style_header),
        Paragraph("Qty", style_header),
        Paragraph("Pur. Price", style_header),
        Paragraph("Sale Price", style_header),
        Paragraph("Gross Prof.", style_header),
        Paragraph("Int. Cost", style_header),
        Paragraph("Net Profit", style_header),
    ]
    
    table_data = [table_headers]
    for row in report_data['items']:
        pdate = row['purchase_date'].strftime("%Y-%m-%d") if isinstance(row['purchase_date'], datetime.date) else str(row['purchase_date'])
        sdate = row['sale_date'].strftime("%Y-%m-%d") if isinstance(row['sale_date'], datetime.date) else str(row['sale_date'])
        
        net_prof = row['net_profit']
        net_prof_str = f"{net_prof:,.2f}"
        if net_prof < 0:
            net_style = ParagraphStyle('net_red', parent=style_cell, textColor=colors.HexColor('#ef4444'))
        else:
            net_style = ParagraphStyle('net_green', parent=style_cell, textColor=colors.HexColor('#10b981'))
            
        table_data.append([
            Paragraph(row['product_code'] or "N/A", style_cell),
            Paragraph(row['product_name'], style_cell),
            Paragraph(pdate, style_cell),
            Paragraph(sdate, style_cell),
            Paragraph(str(row['days']), style_cell),
            Paragraph(str(row['qty']), style_cell),
            Paragraph(f"{row['purchase_price']:,.2f}", style_cell),
            Paragraph(f"{row['sale_price']:,.2f}", style_cell),
            Paragraph(f"{row['gross_profit']:,.2f}", style_cell),
            Paragraph(f"{row['interest_cost']:,.2f}", style_cell),
            Paragraph(net_prof_str, net_style)
        ])
        
    table_data.append([
        Paragraph("<b>TOTALS</b>", style_cell_bold),
        Paragraph("", style_cell),
        Paragraph("", style_cell),
        Paragraph("", style_cell),
        Paragraph("", style_cell),
        Paragraph(str(sum(r['qty'] for r in report_data['items'])), style_cell_bold),
        Paragraph("", style_cell),
        Paragraph("", style_cell),
        Paragraph(f"{report_data['total_gross_profit']:,.2f}", style_cell_bold),
        Paragraph(f"{report_data['total_interest_cost']:,.2f}", style_cell_bold),
        Paragraph(f"{report_data['total_net_profit']:,.2f}", style_cell_bold),
    ])
    
    col_widths = [45, 145, 55, 75, 35, 30, 60, 60, 80, 80, 105]
    
    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e1e38')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f1f5f9')),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#cbd5e1')),
    ]))
    
    story.append(items_table)
    story.append(Spacer(1, 20))
    
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawRightString(806, 20, f"Page {canvas.getPageNumber()}")
        canvas.drawString(36, 20, "Inventory & Accounting Management System - Confidential Report")
        canvas.restoreState()
        
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)







