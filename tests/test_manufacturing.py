import pytest
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, UserRole, UserStatus, AdminProfile, AdminScope
from apps.permissions.models import ModulePermission, PermissionTemplate, AuthorityChangeLog
from apps.permissions.services import apply_permission_template, has_permission, update_user_permission
from apps.products.models import Product, StageChoices, ProductStatus, PriorityChoices
from apps.production.models import BendingRecord, PressingRecord, WeldingRecord, PaintRecord, PDIRecord, ProcessStatus, PressingProcessType
from apps.quality.models import RejectionReason, Rejection, RejectionStatus
from apps.dispatch.models import DispatchRecord, DispatchStatus
from apps.dispatch.services import check_dispatch_eligibility
from apps.audit.models import AuditLog, AuditAction

class ManufacturingSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Super Admin
        self.super_admin = User.objects.create_user(
            email='test.superadmin@example.com',
            username='test_superadmin',
            password='Password123!',
            employee_id='TEST-SA-01',
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True,
            is_superuser=True
        )

        # 2. Production Admin
        self.prod_admin = User.objects.create_user(
            email='test.prodadmin@example.com',
            username='test_prodadmin',
            password='Password123!',
            employee_id='TEST-ADM-01',
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True
        )
        AdminProfile.objects.create(user=self.prod_admin, created_by=self.super_admin)
        AdminScope.objects.create(admin=self.prod_admin)
        apply_permission_template(self.prod_admin, 'Production Admin', changed_by=self.super_admin)

        # 3. Quality Admin
        self.quality_admin = User.objects.create_user(
            email='test.qualityadmin@example.com',
            username='test_qualityadmin',
            password='Password123!',
            employee_id='TEST-ADM-02',
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True
        )
        AdminProfile.objects.create(user=self.quality_admin, created_by=self.super_admin)
        AdminScope.objects.create(admin=self.quality_admin)
        apply_permission_template(self.quality_admin, 'Quality Admin', changed_by=self.super_admin)

        # 4. Operators
        self.bending_user = User.objects.create_user(
            email='test.bending@example.com',
            username='test_bending',
            password='Password123!',
            employee_id='TEST-OP-01',
            role=UserRole.BENDING_OPERATOR,
            production_stage='BENDING',
            status=UserStatus.ACTIVE
        )

        # 5. Sample Product
        self.product = Product.objects.create(
            product_name="Test Tubular Frame",
            part_number="PN-TEST-001",
            customer="Acme Automotive",
            current_stage=StageChoices.BENDING,
            status=ProductStatus.IN_PROGRESS,
            priority=PriorityChoices.HIGH
        )

    def test_super_admin_can_create_admin(self):
        """Super Admin can access admin creation page and provision an Admin."""
        self.client.force_login(self.super_admin)
        response = self.client.get('/admin-panel/admins/create/')
        self.assertEqual(response.status_code, 200)

        post_data = {
            'full_name': 'New Test Admin',
            'employee_id': 'TEST-ADM-99',
            'email': 'new.admin@example.com',
            'username': 'new_admin',
            'phone': '1234567890',
            'department': 'Operations',
            'designation': 'Assistant Admin',
            'password': 'AdminPassword123!',
            'confirm_password': 'AdminPassword123!',
            'status': 'ACTIVE',
        }
        resp = self.client.post('/admin-panel/admins/create/', post_data)
        self.assertEqual(resp.status_code, 302) # Redirects to authority matrix
        self.assertTrue(User.objects.filter(email='new.admin@example.com', role=UserRole.ADMIN).exists())

    def test_normal_admin_cannot_create_admin(self):
        """CRITICAL: Normal Admin CANNOT create an Admin (Strict 403)."""
        self.client.force_login(self.prod_admin)
        response = self.client.get('/admin-panel/admins/create/')
        self.assertEqual(response.status_code, 403)

        response = self.client.post('/admin-panel/admins/create/', {'email': 'hacker@example.com'})
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_access_admin_panel(self):
        """Normal operators cannot access /admin-panel/ (Strict 403)."""
        self.client.force_login(self.bending_user)
        response = self.client.get('/admin-panel/dashboard/')
        self.assertEqual(response.status_code, 403)

    def test_admin_unauthorized_module_access(self):
        """Admin without module permission cannot access restricted views (e.g. Quality Admin accessing Welding)."""
        self.assertFalse(has_permission(self.quality_admin, 'welding', 'view'))

        self.client.force_login(self.quality_admin)
        response = self.client.get('/admin-panel/production/welding/')
        self.assertEqual(response.status_code, 403)

    def test_authority_matrix_update(self):
        """Super Admin modifying admin authority grants/revokes permissions dynamically."""
        self.assertFalse(has_permission(self.prod_admin, 'paint', 'view'))

        # Grant paint view to prod_admin
        update_user_permission(
            self.prod_admin,
            'paint',
            {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_approve': False, 'can_export': False},
            changed_by=self.super_admin
        )
        self.assertTrue(has_permission(self.prod_admin, 'paint', 'view'))

    def test_suspended_admin_blocked(self):
        """Suspended Admin is immediately blocked by middleware upon request."""
        self.prod_admin.status = UserStatus.SUSPENDED
        self.prod_admin.save()

        self.client.force_login(self.prod_admin)
        response = self.client.get('/admin-panel/dashboard/')
        # UserStatusCheckMiddleware redirects suspended user to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_manufacturing_workflow_and_dispatch_gatekeeper(self):
        """
        Tests the complete 6-stage manufacturing progression:
        Product -> Bending -> Pressing -> Welding -> Paint -> PDI -> Dispatch.
        Verifies that Dispatch is strictly BLOCKED until all stages are passed!
        """
        # Initially in BENDING: Dispatch must be BLOCKED
        eligible, issues, statuses = check_dispatch_eligibility(self.product)
        self.assertFalse(eligible)
        self.assertIn("Bending", issues[0])

        # 1. Complete Bending
        BendingRecord.objects.create(
            product=self.product,
            tube_size="38.1 mm",
            thickness="2.0 mm",
            critical_dimension_status="PASS",
            status=ProcessStatus.COMPLETED
        )
        self.product.current_stage = StageChoices.PRESSING
        self.product.save()

        # Still blocked (Pressing not complete)
        eligible, issues, _ = check_dispatch_eligibility(self.product)
        self.assertFalse(eligible)

        # 2. Complete Pressing (Blanking, Forming, Pearling, Restricting)
        for ptype in ['BLANKING', 'FORMING', 'PEARLING', 'RESTRICTING']:
            PressingRecord.objects.create(
                product=self.product,
                process_type=ptype,
                critical_dimension_result="PASS",
                status=ProcessStatus.COMPLETED
            )
        self.product.current_stage = StageChoices.WELDING
        self.product.save()

        # 3. Complete Welding (Stages 1-5)
        for snum in range(1, 6):
            WeldingRecord.objects.create(
                product=self.product,
                stage_number=snum,
                stage_name=f"Stage {snum}",
                result="PASS",
                status=ProcessStatus.COMPLETED
            )
        self.product.current_stage = StageChoices.PAINT
        self.product.save()

        # 4. Paint sign-offs
        paint = PaintRecord.objects.create(
            product=self.product,
            paint_specification="Powder Coat",
            color_code="RAL 7016",
            thickness_microns=85.0,
            ceo_approved=True,
            pc_approved=True,
            status=ProcessStatus.APPROVED
        )
        self.product.current_stage = StageChoices.PDI
        self.product.save()

        # Still blocked because PDI is pending
        eligible, issues, _ = check_dispatch_eligibility(self.product)
        self.assertFalse(eligible)
        self.assertIn("PDI", issues[0])

        # 5. PDI approval
        PDIRecord.objects.create(
            product=self.product,
            is_approved=True,
            status=ProcessStatus.APPROVED
        )
        self.product.current_stage = StageChoices.DISPATCH
        self.product.save()

        # NOW ELIGIBLE FOR DISPATCH!
        eligible, issues, statuses = check_dispatch_eligibility(self.product)
        self.assertTrue(eligible)
        self.assertEqual(len(issues), 0)
        self.assertEqual(statuses['bending'], 'PASSED')
        self.assertEqual(statuses['pressing'], 'PASSED')
        self.assertEqual(statuses['welding'], 'PASSED')
        self.assertEqual(statuses['paint'], 'PASSED')
        self.assertEqual(statuses['pdi'], 'PASSED')

    def test_qr_code_generation(self):
        """Product creation automatically generates a QR code image with embedded payload."""
        prod = Product.objects.create(
            product_name="QR Tested Frame",
            part_number="PN-QR-100",
            customer="Universal Motors"
        )
        self.assertIsNotNone(prod.qr_code_image)
        self.assertTrue(prod.product_id.startswith('PROD-'))
        self.assertIn(prod.product_id, prod.qr_data)
