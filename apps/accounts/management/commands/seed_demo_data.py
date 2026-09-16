import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.base import ContentFile
from apps.accounts.models import User, UserRole, UserStatus, AdminProfile, AdminScope
from apps.permissions.models import ModulePermission, PermissionTemplate
from apps.permissions.services import apply_permission_template, DEFAULT_TEMPLATES
from apps.products.models import Product, ProductPart, StageChoices, ProductStatus, PriorityChoices
from apps.production.models import BendingRecord, PressingRecord, WeldingRecord, PaintRecord, PDIRecord, ProcessStatus, PressingProcessType
from apps.quality.models import RejectionReason, CriticalDimension, Inspection, InspectionParameter, Rejection, RejectionStatus
from apps.documents.models import Document, DocumentCategory, DocumentStatus, ApprovedSample
from apps.dispatch.models import DispatchRecord, DispatchStatus
from apps.audit.models import AuditLog, AuditAction

class Command(BaseCommand):
    help = "Seeds comprehensive manufacturing demo data including Super Admin, Admins, Operators, Products, and Workflow stages."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing Manufacturing System Demo Data Seeding..."))

        # 1. Create Default Permission Templates in DB
        for name, matrix in DEFAULT_TEMPLATES.items():
            PermissionTemplate.objects.update_or_create(
                name=name,
                defaults={'matrix': matrix, 'description': f"Standard predefined {name} permissions"}
            )
        self.stdout.write(self.style.SUCCESS("[OK] Permission templates verified."))

        # 2. Create Rejection Reasons
        reasons_data = [
            ("Dimension Mismatch", "DEF-DIM", "Component critical dimension exceeds engineering tolerance limits"),
            ("Welding Defect", "DEF-WELD", "Incomplete penetration, blowholes, porosity or weld crack detected"),
            ("Paint Defect", "DEF-PAINT", "Blistering, paint runs, orange peel effect or insufficient thickness"),
            ("Surface Damage", "DEF-SURF", "Deep dent, gouge or scratch on critical sealing surface"),
            ("Wrong Component", "DEF-PART", "Incorrect part number or sub-assembly component loaded"),
            ("Documentation Issue", "DEF-DOC", "Missing inspection report, unapproved drawing, or sign-off discrepancy"),
            ("Packing Issue", "DEF-PACK", "Damaged packaging, missing rust inhibitor VCI, or broken crate"),
            ("Other", "DEF-MISC", "Miscellaneous non-conformance"),
        ]
        for name, code, desc in reasons_data:
            RejectionReason.objects.update_or_create(name=name, defaults={'code': code, 'description': desc, 'is_active': True})
        self.stdout.write(self.style.SUCCESS("[OK] Rejection reasons seeded."))

        # 3. Create Super Admin
        super_admin, created = User.objects.get_or_create(
            email='superadmin@example.com',
            defaults={
                'username': 'superadmin',
                'full_name': 'Chief Super Administrator',
                'employee_id': 'EMP-SA-001',
                'role': UserRole.SUPER_ADMIN,
                'status': UserStatus.ACTIVE,
                'department': 'Executive Management',
                'designation': 'Chief Operating Officer',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        super_admin.set_password('SuperAdmin123!')
        super_admin.role = UserRole.SUPER_ADMIN
        super_admin.is_staff = True
        super_admin.is_superuser = True
        super_admin.save()
        self.stdout.write(self.style.SUCCESS("[OK] Super Admin: superadmin@example.com (SuperAdmin123!)"))

        # 4. Create Department Admins
        admins_data = [
            ('production.admin@example.com', 'prod_admin', 'Production Manager', 'EMP-ADM-001', 'Production Admin', 'Production Fabrication'),
            ('quality.admin@example.com', 'quality_admin', 'Quality Assurance Head', 'EMP-ADM-002', 'Quality Admin', 'Quality Assurance'),
            ('dispatch.admin@example.com', 'dispatch_admin', 'Logistics Director', 'EMP-ADM-003', 'Dispatch Admin', 'Supply Chain & Logistics'),
        ]
        admin_objs = {}
        for email, username, full_name, emp_id, template_name, dept in admins_data:
            admin_user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'full_name': full_name,
                    'employee_id': emp_id,
                    'role': UserRole.ADMIN,
                    'status': UserStatus.ACTIVE,
                    'department': dept,
                    'designation': full_name,
                    'is_staff': True,
                }
            )
            admin_user.set_password('AdminPass123!')
            admin_user.role = UserRole.ADMIN
            admin_user.is_staff = True
            admin_user.save()

            AdminProfile.objects.update_or_create(
                user=admin_user,
                defaults={'department': dept, 'designation': full_name, 'created_by': super_admin}
            )
            AdminScope.objects.update_or_create(
                admin=admin_user,
                defaults={'stages': [], 'departments': [dept]}
            )
            apply_permission_template(admin_user, template_name, changed_by=super_admin)
            admin_objs[email] = admin_user
            self.stdout.write(self.style.SUCCESS(f"[OK] Admin: {email} (AdminPass123!) -> {template_name}"))

        # 5. Create Operators & Shop Floor Users
        operators_data = [
            ('bending.user@example.com', 'bending_op', 'Marcus Vance', 'EMP-OP-101', UserRole.BENDING_OPERATOR, 'BENDING', 'Line 1 - Mandrel Bending', 'Morning Shift'),
            ('welding.user@example.com', 'welding_op', 'Elena Rostova', 'EMP-OP-102', UserRole.WELDING_OPERATOR, 'WELDING', 'Cell 3 - Robotic MIG', 'Morning Shift'),
            ('paint.user@example.com', 'paint_op', 'Kenji Sato', 'EMP-OP-103', UserRole.PAINT_OPERATOR, 'PAINT', 'Booth A - Powder Coat', 'Afternoon Shift'),
            ('pdi.user@example.com', 'pdi_op', 'Sarah Jenkins', 'EMP-OP-104', UserRole.PDI_INSPECTOR, 'PDI', 'QA Inspection Bay', 'Morning Shift'),
            ('dispatch.user@example.com', 'dispatch_op', 'David Miller', 'EMP-OP-105', UserRole.DISPATCH_OPERATOR, 'DISPATCH', 'Dock Bay 4', 'General Shift'),
        ]
        operator_objs = {}
        for email, username, full_name, emp_id, role, stage, line, shift in operators_data:
            op_user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'full_name': full_name,
                    'employee_id': emp_id,
                    'role': role,
                    'status': UserStatus.ACTIVE,
                    'production_stage': stage,
                    'production_line': line,
                    'shift': shift,
                    'assigned_admin': admin_objs['production.admin@example.com'],
                }
            )
            op_user.set_password('UserPass123!')
            op_user.save()
            operator_objs[email] = op_user
            self.stdout.write(self.style.SUCCESS(f"[OK] Operator: {email} (UserPass123!) -> {stage}"))

        # 6. Create Controlled Documents
        sample_doc_content = b"%PDF-1.4 Demonstration Engineering Manufacturing Control Document\n1 0 obj<<>>endobj\ntrailer<<>>%%EOF"
        docs_specs = [
            ("Master Chassis Tube Bending Drawing", DocumentCategory.DRAWINGS, "1.2", 3, "DWG-CH-001"),
            ("Process Flow Diagram (PFD) - Exhaust Manifold", DocumentCategory.PFD, "2.0", 1, "PFD-EX-2026"),
            ("Failure Mode and Effects Analysis (PFMEA)", DocumentCategory.PFMEA, "1.0", 0, "PFMEA-HYD-01"),
            ("Comprehensive Quality Control Plan (CP)", DocumentCategory.CP, "3.1", 4, "CP-GLOBAL-04"),
            ("Process Sheet (PS) - Robotic Welding Sequence", DocumentCategory.PS, "1.5", 2, "PS-WELD-R5"),
            ("Packaging & Anti-Corrosive Standard Specification", DocumentCategory.PACKING_STANDARD, "1.0", 0, "PKG-STD-VCI"),
        ]
        for name, cat, ver, rev, part in docs_specs:
            doc, _ = Document.objects.update_or_create(
                name=name,
                defaults={
                    'document_type': cat,
                    'version': ver,
                    'revision': rev,
                    'part_number': part,
                    'uploaded_by': super_admin,
                    'description': f"Official engineering release for {name}",
                }
            )
            if not doc.file:
                doc.file.save(f"{part}.pdf", ContentFile(sample_doc_content), save=True)

        # 7. Create Products across different Pipeline Stages
        products_spec = [
            ("PROD-2026-00001", "Automotive Subframe Assembly", "PN-SUB-9021", "Toyota Motors", "Corolla Hybrid", "BATCH-A1", StageChoices.BENDING, ProductStatus.IN_PROGRESS, PriorityChoices.HIGH),
            ("PROD-2026-00002", "Heavy Duty Suspension Linkage", "PN-SUS-4410", "Volvo Trucks", "FH-16", "BATCH-B4", StageChoices.PRESSING, ProductStatus.IN_PROGRESS, PriorityChoices.MEDIUM),
            ("PROD-2026-00003", "Exhaust Flange & Manifold Joint", "PN-EXH-7782", "Hyundai Heavy", "HX-220", "BATCH-C2", StageChoices.WELDING, ProductStatus.IN_PROGRESS, PriorityChoices.URGENT),
            ("PROD-2026-00004", "Hydraulic Cylinder Outer Tube", "PN-HYD-1190", "Caterpillar Inc", "CAT-336", "BATCH-D8", StageChoices.PAINT, ProductStatus.PENDING, PriorityChoices.MEDIUM),
            ("PROD-2026-00005", "Steering Column Support Arm", "PN-STR-5520", "Ford Global", "F-150 Lightning", "BATCH-E5", StageChoices.PDI, ProductStatus.IN_PROGRESS, PriorityChoices.HIGH),
            ("PROD-2026-00006", "High Tensile Crash Barrier Strut", "PN-BAR-3301", "Mercedes-Benz", "Actros", "BATCH-F9", StageChoices.DISPATCH, ProductStatus.APPROVED, PriorityChoices.URGENT),
            ("PROD-2026-00007", "Rear Axle Reinforcement Tube", "PN-AXL-8822", "Tata Motors", "Harrier EV", "BATCH-G3", StageChoices.BENDING, ProductStatus.REJECTED, PriorityChoices.MEDIUM),
        ]

        for pid, name, part, cust, model, batch, stage, status, priority in products_spec:
            prod, _ = Product.objects.update_or_create(
                product_id=pid,
                defaults={
                    'product_name': name,
                    'part_number': part,
                    'customer': cust,
                    'model': model,
                    'batch_number': batch,
                    'current_stage': stage,
                    'status': status,
                    'priority': priority,
                    'assigned_admin': admin_objs['production.admin@example.com'],
                    'assigned_user': operator_objs['bending.user@example.com'],
                }
            )
            # Ensure QR code exists
            if not prod.qr_code_image:
                prod.generate_qr_code(save_instance=True)

            # Stage specific setup
            if pid == "PROD-2026-00001": # Bending active
                BendingRecord.objects.get_or_create(
                    product=prod,
                    defaults={
                        'tube_size': '38.1 mm',
                        'thickness': '2.0 mm',
                        'critical_dimension_status': 'PASS',
                        'status': ProcessStatus.IN_PROGRESS,
                        'operator': operator_objs['bending.user@example.com'],
                    }
                )

            elif pid == "PROD-2026-00002": # Pressing in progress
                BendingRecord.objects.get_or_create(
                    product=prod,
                    defaults={'status': ProcessStatus.COMPLETED, 'critical_dimension_status': 'PASS'}
                )
                PressingRecord.objects.get_or_create(
                    product=prod,
                    process_type=PressingProcessType.BLANKING,
                    defaults={'status': ProcessStatus.COMPLETED, 'dim_report_number': 'DIM-2026-091'}
                )
                PressingRecord.objects.get_or_create(
                    product=prod,
                    process_type=PressingProcessType.FORMING,
                    defaults={'status': ProcessStatus.IN_PROGRESS}
                )

            elif pid == "PROD-2026-00003": # Welding in progress
                BendingRecord.objects.get_or_create(product=prod, defaults={'status': ProcessStatus.COMPLETED, 'critical_dimension_status': 'PASS'})
                for ptype in [PressingProcessType.BLANKING, PressingProcessType.FORMING, PressingProcessType.PEARLING, PressingProcessType.RESTRICTING]:
                    PressingRecord.objects.get_or_create(product=prod, process_type=ptype, defaults={'status': ProcessStatus.COMPLETED})
                WeldingRecord.objects.get_or_create(
                    product=prod, stage_number=1,
                    defaults={'stage_name': 'Stage 1', 'status': ProcessStatus.COMPLETED, 'approved_sample_id': 'SAMPLE-2026-0001'}
                )
                WeldingRecord.objects.get_or_create(
                    product=prod, stage_number=2,
                    defaults={'stage_name': 'Stage 2', 'status': ProcessStatus.IN_PROGRESS}
                )

            elif pid == "PROD-2026-00004": # Paint awaiting approvals
                BendingRecord.objects.get_or_create(product=prod, defaults={'status': ProcessStatus.COMPLETED, 'critical_dimension_status': 'PASS'})
                for ptype in [PressingProcessType.BLANKING, PressingProcessType.FORMING, PressingProcessType.PEARLING, PressingProcessType.RESTRICTING]:
                    PressingRecord.objects.get_or_create(product=prod, process_type=ptype, defaults={'status': ProcessStatus.COMPLETED})
                for snum in range(1, 6):
                    WeldingRecord.objects.get_or_create(product=prod, stage_number=snum, defaults={'status': ProcessStatus.COMPLETED, 'stage_name': f'Stage {snum}'})
                PaintRecord.objects.get_or_create(
                    product=prod,
                    defaults={
                        'status': ProcessStatus.IN_PROGRESS,
                        'ceo_approved': False,
                        'pc_approved': True,
                        'pc_approved_by': admin_objs['production.admin@example.com'],
                        'pc_approval_date': timezone.now()
                    }
                )

            elif pid == "PROD-2026-00005": # PDI inspection
                BendingRecord.objects.get_or_create(product=prod, defaults={'status': ProcessStatus.COMPLETED, 'critical_dimension_status': 'PASS'})
                for ptype in [PressingProcessType.BLANKING, PressingProcessType.FORMING, PressingProcessType.PEARLING, PressingProcessType.RESTRICTING]:
                    PressingRecord.objects.get_or_create(product=prod, process_type=ptype, defaults={'status': ProcessStatus.COMPLETED})
                for snum in range(1, 6):
                    WeldingRecord.objects.get_or_create(product=prod, stage_number=snum, defaults={'status': ProcessStatus.COMPLETED, 'stage_name': f'Stage {snum}'})
                PaintRecord.objects.get_or_create(
                    product=prod,
                    defaults={'status': ProcessStatus.COMPLETED, 'ceo_approved': True, 'pc_approved': True, 'ceo_approved_by': super_admin, 'pc_approved_by': admin_objs['production.admin@example.com']}
                )
                PDIRecord.objects.get_or_create(product=prod, defaults={'status': ProcessStatus.IN_PROGRESS})

            elif pid == "PROD-2026-00006": # CLEARED FOR DISPATCH (All 5 stages passed)
                BendingRecord.objects.get_or_create(product=prod, defaults={'status': ProcessStatus.COMPLETED, 'critical_dimension_status': 'PASS'})
                for ptype in [PressingProcessType.BLANKING, PressingProcessType.FORMING, PressingProcessType.PEARLING, PressingProcessType.RESTRICTING]:
                    PressingRecord.objects.get_or_create(product=prod, process_type=ptype, defaults={'status': ProcessStatus.COMPLETED})
                for snum in range(1, 6):
                    WeldingRecord.objects.get_or_create(product=prod, stage_number=snum, defaults={'status': ProcessStatus.COMPLETED, 'stage_name': f'Stage {snum}'})
                PaintRecord.objects.get_or_create(
                    product=prod,
                    defaults={'status': ProcessStatus.COMPLETED, 'ceo_approved': True, 'pc_approved': True, 'ceo_approved_by': super_admin, 'pc_approved_by': admin_objs['production.admin@example.com']}
                )
                PDIRecord.objects.get_or_create(
                    product=prod,
                    defaults={'status': ProcessStatus.APPROVED, 'is_approved': True, 'approved_by': operator_objs['pdi.user@example.com']}
                )
                DispatchRecord.objects.get_or_create(
                    product=prod,
                    defaults={
                        'customer': prod.customer,
                        'status': DispatchStatus.READY,
                        'vehicle_number': 'MH-14-GH-2210',
                        'transporter': 'DHL Supply Chain Express',
                        'invoice_number': 'INV-2026-00488',
                    }
                )

            elif pid == "PROD-2026-00007": # REJECTED IN BENDING
                BendingRecord.objects.get_or_create(
                    product=prod,
                    defaults={'status': ProcessStatus.HOLD, 'critical_dimension_status': 'FAIL'}
                )
                dim_reason = RejectionReason.objects.get(name="Dimension Mismatch")
                Rejection.objects.get_or_create(
                    product=prod,
                    stage='BENDING',
                    defaults={
                        'reason': dim_reason,
                        'description': 'Tube bend radius deviation +3.5mm exceeding maximum drawing limit.',
                        'created_by': operator_objs['bending.user@example.com'],
                        'status': RejectionStatus.OPEN,
                        'corrective_action': 'Recalibrate CNC Bending mandrel position and scrap defective lot.'
                    }
                )

        # 8. Create Initial System Audit Trail Event
        AuditLog.objects.create(
            user=super_admin,
            action=AuditAction.ADMIN_ACTIVATED,
            entity='System',
            entity_id='GLOBAL',
            new_value="Manufacturing Management Application initialized and demo seeds populated.",
            ip_address="127.0.0.1"
        )

        self.stdout.write(self.style.SUCCESS("[OK] Successfully populated all demo data, products, stages, and audit logs!"))
