"""Report generation service – PDF, CSV, and Excel exports."""
import io
import csv
import calendar
from datetime import date, datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class ReportService:
    """Generate PDF and tabular reports."""

    @staticmethod
    def generate_salary_slip_pdf(payroll_record):
        """Generate a salary slip PDF for a single payroll record."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               topMargin=30*mm, bottomMargin=20*mm,
                               leftMargin=20*mm, rightMargin=20*mm)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                     alignment=TA_CENTER, fontSize=18,
                                     spaceAfter=6, textColor=colors.HexColor('#1a2332'))
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                        alignment=TA_CENTER, fontSize=10,
                                        textColor=colors.grey)
        section_style = ParagraphStyle('Section', parent=styles['Heading3'],
                                       fontSize=12, textColor=colors.HexColor('#1a2332'),
                                       spaceAfter=4, spaceBefore=12)

        elements = []
        emp = payroll_record.employee
        pr = payroll_record
        month_name = calendar.month_name[pr.pay_month]

        # Header
        elements.append(Paragraph('SALARY SLIP', title_style))
        elements.append(Paragraph(f'{month_name} {pr.pay_year}', subtitle_style))
        elements.append(Spacer(1, 4*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a2332')))
        elements.append(Spacer(1, 4*mm))

        # Employee info table
        info_data = [
            ['Employee Code:', emp.employee_code, 'Department:', emp.department.name],
            ['Name:', emp.full_name, 'Designation:', emp.designation],
            ['Email:', emp.email, 'Location:', emp.work_location or 'N/A'],
            ['Pay Period:', f'{pr.pay_period_start} to {pr.pay_period_end}',
             'Status:', pr.status.upper()],
        ]
        info_table = Table(info_data, colWidths=[90, 150, 90, 150])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 6*mm))

        # Earnings and Deductions side by side
        elements.append(Paragraph('Earnings & Deductions', section_style))

        earnings = [
            ['EARNINGS', 'AMOUNT (₹)'],
            ['Basic Salary', f'{pr.basic_salary:,.2f}'],
            ['House Rent Allowance', f'{pr.hra:,.2f}'],
            ['Other Allowances', f'{pr.other_allowances:,.2f}'],
            ['Bonus / Incentives', f'{pr.bonus:,.2f}'],
            ['Overtime Pay', f'{pr.overtime_pay:,.2f}'],
            ['', ''],
            ['GROSS SALARY', f'{pr.gross_salary:,.2f}'],
        ]

        deductions = [
            ['DEDUCTIONS', 'AMOUNT (₹)'],
            ['Tax Deduction *', f'{pr.tax_deduction:,.2f}'],
            ['Provident Fund *', f'{pr.pf_deduction:,.2f}'],
            ['Other Deductions', f'{pr.other_deductions:,.2f}'],
            ['Unpaid Leave Ded.', f'{pr.unpaid_leave_deduction:,.2f}'],
            ['', ''],
            ['', ''],
            ['TOTAL DEDUCTIONS', f'{pr.total_deductions:,.2f}'],
        ]

        col_w = 120
        earn_table = Table(earnings, colWidths=[col_w, col_w])
        earn_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2332')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
        ]))

        ded_table = Table(deductions, colWidths=[col_w, col_w])
        ded_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2332')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fde8e8')),
        ]))

        combined = Table([[earn_table, ded_table]], colWidths=[250, 250])
        combined.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        elements.append(combined)
        elements.append(Spacer(1, 6*mm))

        # Net salary
        net_data = [['NET SALARY', f'₹ {pr.net_salary:,.2f}']]
        net_table = Table(net_data, colWidths=[240, 240])
        net_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0d9488')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(net_table)
        elements.append(Spacer(1, 6*mm))

        # Attendance summary
        att_data = [
            ['Attendance Summary', ''],
            ['Working Days', str(pr.working_days)],
            ['Days Present', str(pr.days_present)],
            ['Days Absent', str(pr.days_absent)],
        ]
        att_table = Table(att_data, colWidths=[240, 240])
        att_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
        ]))
        elements.append(att_table)
        elements.append(Spacer(1, 8*mm))

        # Disclaimer
        disclaimer = Paragraph(
            '<i>* Tax and PF rates are configurable demonstration values. '
            'Verify with your payroll department before relying on these figures.</i>',
            ParagraphStyle('Disclaimer', fontSize=7, textColor=colors.grey)
        )
        elements.append(disclaimer)
        elements.append(Spacer(1, 4*mm))

        # Generation timestamp
        gen_text = Paragraph(
            f'<i>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}</i>',
            ParagraphStyle('GenDate', fontSize=7, textColor=colors.grey, alignment=TA_RIGHT)
        )
        elements.append(gen_text)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_employee_report_pdf(employees):
        """Generate employee directory PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                               topMargin=20*mm, bottomMargin=15*mm,
                               leftMargin=15*mm, rightMargin=15*mm)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph('Employee Directory Report', styles['Title']))
        elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 6*mm))

        data = [['Code', 'Name', 'Department', 'Designation', 'Email', 'Status', 'Joined']]
        for emp in employees:
            data.append([
                emp.employee_code, emp.full_name,
                emp.department.name if emp.department else 'N/A',
                emp.designation, emp.email, emp.employment_status,
                emp.date_of_joining.strftime('%Y-%m-%d') if emp.date_of_joining else 'N/A'
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2332')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_payroll_summary_pdf(records, month, year):
        """Generate monthly payroll summary PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                               topMargin=20*mm, bottomMargin=15*mm,
                               leftMargin=15*mm, rightMargin=15*mm)
        styles = getSampleStyleSheet()
        elements = []

        month_name = calendar.month_name[month]
        elements.append(Paragraph(f'Payroll Summary – {month_name} {year}', styles['Title']))
        elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 6*mm))

        import numpy as np
        if records:
            nets = [r.net_salary for r in records]
            elements.append(Paragraph(
                f'Total: ₹{sum(nets):,.2f}  |  Count: {len(records)}  |  '
                f'Avg: ₹{np.mean(nets):,.2f}  |  Median: ₹{np.median(nets):,.2f}',
                styles['Normal']
            ))
            elements.append(Spacer(1, 4*mm))

        data = [['Code', 'Name', 'Dept', 'Basic', 'HRA', 'Allow.', 'Gross',
                 'Tax', 'PF', 'Deductions', 'Net', 'Status']]
        for r in records:
            data.append([
                r.employee.employee_code, r.employee.full_name,
                r.employee.department.name if r.employee.department else '',
                f'{r.basic_salary:,.0f}', f'{r.hra:,.0f}', f'{r.other_allowances:,.0f}',
                f'{r.gross_salary:,.0f}', f'{r.tax_deduction:,.0f}', f'{r.pf_deduction:,.0f}',
                f'{r.total_deductions:,.0f}', f'{r.net_salary:,.0f}', r.status
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2332')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('ALIGN', (3, 1), (-2, -1), 'RIGHT'),
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_attendance_report_pdf(records, title='Attendance Report'):
        """Generate attendance report PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                               topMargin=20*mm, bottomMargin=15*mm,
                               leftMargin=15*mm, rightMargin=15*mm)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(title, styles['Title']))
        elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}  |  Records: {len(records)}', styles['Normal']))
        elements.append(Spacer(1, 6*mm))

        data = [['Code', 'Name', 'Department', 'Date', 'Check In', 'Check Out',
                 'Hours', 'OT', 'Status', 'Remarks']]
        for r in records[:500]:  # limit for PDF size
            data.append([
                r.employee.employee_code, r.employee.full_name,
                r.employee.department.name, r.attendance_date.strftime('%Y-%m-%d'),
                r.check_in.strftime('%H:%M') if r.check_in else '-',
                r.check_out.strftime('%H:%M') if r.check_out else '-',
                f'{r.working_hours:.1f}', f'{r.overtime_hours:.1f}',
                r.status, (r.remarks or '')[:30]
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2332')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_performance_report_pdf(records, title='Performance Report'):
        """Generate performance evaluation report PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                               topMargin=20*mm, bottomMargin=15*mm,
                               leftMargin=15*mm, rightMargin=15*mm)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(title, styles['Title']))
        elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 6*mm))

        data = [['Code', 'Name', 'Department', 'Period', 'Tasks', 'Completed',
                 'Quality', 'Punctuality', 'Teamwork', 'Overall', 'Rating']]
        for r in records:
            data.append([
                r.employee.employee_code, r.employee.full_name,
                r.employee.department.name, r.evaluation_period,
                str(r.tasks_assigned), str(r.tasks_completed),
                f'{r.quality_score:.0f}', f'{r.punctuality_score:.0f}',
                f'{r.teamwork_score:.0f}', f'{r.overall_score:.1f}', r.rating
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2332')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('ALIGN', (4, 1), (-2, -1), 'CENTER'),
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer
