from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.signals import user_logged_in
import time, datetime
from datetime import date, timedelta
from decimal import Decimal
import requests

def login_handler(sender, user, request, **kwargs):
    try:
        user_agent_info = request.META.get('HTTP_USER_AGENT', '<unknown>')[:255],
        ip = get_client_ip(request)
        user_login_activity_log = UserLoginActivity(login_IP=ip,
                                                    login_username=user.email,
                                                    user_agent_info=user_agent_info,
                                                    status=UserLoginActivity.SUCCESS)
        user_login_activity_log.save()

        try: # Update user state to reflect referral code
            USER_STEP = user.user_funnel_step
            if (USER_STEP == 0): # Uninitialized
                USER_PK = user.id
                ORIG_REFCODE = user.referral_code # Inviter's Referral code gets copied into referral_parent
                NEW_REF_CODE = str(ORIG_REFCODE)
                NEW_REF_CODE = NEW_REF_CODE[:3]  # Take the first 3 digits
                NEWCODE = NEW_REF_CODE + str(USER_PK) # + USER_PK
                user.referral_code = NEWCODE
                # Successfully generated referral code 
                # Now save the parent and finalize
                user.referral_parent = ORIG_REFCODE
                user.user_funnel_step = 1
                user.save()
            if (USER_STEP == 1):
                print(USER_STEP, user.id, user.referral_code)

            if (USER_STEP >= 4):
                if (user.referral_credit_used == 0):
                    # Give a referral credit to the referrer in 30 days
                    REFERRAL_PARENT = int(user.referral_parent)
                    today_date = date.today()
                    td = timedelta(30)
                    # select the parent
                    parent_user = User.objects.get(id=REFERRAL_PARENT)
                    try:  # Calculate the $20 reward at current market rate
                        BTC_USD = requests.post('http://localhost:8000/api/fx/BTC_USD').content.decode('utf-8')
                        BTC_USD = Decimal(BTC_USD[1:-1]) # remove the quotes
                        bonus_credit_bits = round((20 / BTC_USD)*1000000, 0)
                        print("CREDIT IN 30 DAYS:", today_date + td, bonus_credit_bits, "bits")
                        referral = Referral(referral_from_user=user, referral_to_user=parent_user, referral_registered=datetime.datetime.now(), referral_type=1, referral_amount_bits=bonus_credit_bits,credited_on=today_date + td)
                        referral.save()
                        user.user_funnel_step = 41
                        user.referral_credit_used = 1
                        user.save()
                    except:
                        print("failed to credit referral", user.id)

        except:
            print("nayobka")
    except Exception as e:
        # log the error
        error_log.error("log_user_logged_in request: %s, error: %s" % (request, e))
    
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

user_logged_in.connect(login_handler)

class Permission(models.Model):
    name = models.CharField(max_length=200)
    def __str__(self):
        return str(self.name)


class Role(models.Model):
    name = models.CharField(max_length=200)
    permissions = models.ManyToManyField(Permission)
    def __str__(self):
        return str(self.name)


class User(AbstractUser):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    email = models.CharField(max_length=200, unique=True)
    password = models.CharField(max_length=200)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)
    username = None

    # CUSTOM STUFF
    user_id = models.IntegerField(blank=True, null=True)
    referral_code = models.IntegerField(blank=True, default=1)
    referral_parent = models.IntegerField(blank=True, default=1)
    account_type = models.CharField(('account type'), max_length=40, blank=True, null=True, unique=False, default="basic")
    acct_xp_points = models.IntegerField(blank=True, default=0)
    primary_phone = models.IntegerField(blank=True, default=0)
    phone = models.CharField(max_length=12, null=True, default=0, blank=True)
    secondary_phone = models.IntegerField(blank=True, default=0)
    BTC_user_referral_bonus = models.DecimalField(max_digits=23, decimal_places=8, null=True, default=0, blank=True)
    BTC_external_withdraw_address = models.CharField(max_length=43, blank=True, null=True, unique=False)
    BTC_deposit_address = models.CharField(max_length=34, blank=True, null=True, unique=False)
    BTC_outstanding_balance = models.DecimalField(('BTC_outstanding_balance'), max_digits=23, decimal_places=8, null=True, default=0, blank=True)
    BTC_confirmed_balance = models.DecimalField(('BTC_confirmed_balance'), max_digits=23, decimal_places=8, null=True, default=0, blank=True)
    current_invoice_id = models.IntegerField(null=True, blank=True)
    last_btc_tx_hash = models.CharField(null=True, blank=True, max_length=64)
    invoices_paid = models.IntegerField(null=True, blank=True, default=0)
    last_invoice_amount = models.DecimalField(max_digits=23, decimal_places=8, null=True, default=0, blank=True)
    btc_credit = models.DecimalField(max_digits=23, decimal_places=8, null=True, default=0, blank=True)
    btc_invoices_paid = models.DecimalField(max_digits=23, decimal_places=8, null=True, default=0, blank=True)
    user_funnel_step = models.IntegerField(null=True, blank=True, default=0) 
    referral_credit_used = models.BooleanField(null=True, blank=True, default=0)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    def __str__(self):
        return str(self.id)
    def get_user_short(self):
        return str(self.first_name) + " " + str(self.last_name) + " " + str(self.email)


class Referral(models.Model):
    referral_from_user = models.ForeignKey(User, related_name='referral_from_user', on_delete=models.CASCADE)
    referral_to_user = models.ForeignKey(User, related_name='referral_to_user', on_delete=models.CASCADE)
    referral_type = models.IntegerField(blank=True, default=1)
    referral_status = models.BooleanField(blank=True, default=False)
    referral_registered = models.DateTimeField('referral_registered', null=True, blank=True)
    referral_amount_BTC = models.DecimalField(max_digits=19, decimal_places=8, null=True, default=0, blank=True)
    credited_on = models.DateField(blank=True, null=True)
    def __str__(self):
        return str(self.referral_type)


class UserLoginActivity(models.Model):
    # Login Status
    SUCCESS = 'S'
    FAILED = 'F'

    LOGIN_STATUS = ((SUCCESS, 'Success'),
                           (FAILED, 'Failed'))

    login_IP = models.GenericIPAddressField(null=True, blank=True)
    login_datetime = models.DateTimeField(auto_now=True)
    login_username = models.CharField(max_length=40, null=True, blank=True)
    status = models.CharField(max_length=1, default=SUCCESS, choices=LOGIN_STATUS, null=True, blank=True)
    user_agent_info = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'user_login_activity'
        verbose_name_plural = 'user_login_activities'
    def __str__(self):
        return str(self.login_username) + " | " + str(self.login_IP)