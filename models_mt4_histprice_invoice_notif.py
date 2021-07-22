from django.db import models
from django.contrib.auth.models import AbstractUser
from users.models import User

class Product(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=1000)
    image = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.title

class MTConnection(models.Model):
    acct_owner_id = models.ForeignKey(User, related_name='user_id', blank=True, default=1, on_delete=models.CASCADE)
    created = models.DateField(
        auto_now_add=True, editable=False, null=False, blank=False)
    last_modified = models.DateField(
        auto_now=True, editable=False, null=False, blank=False)
    last_modified_ts = models.DateTimeField(auto_now=True, null=True, blank=True)
    mt4_password = models.CharField(blank=True, max_length=255)
    mt4_server = models.CharField(blank=True, max_length=200)
    mt4_broker = models.CharField(blank=True, max_length=200)
    mt4_notes = models.TextField(blank=True, max_length=255)
    mt4_acct_status = models.BooleanField(blank=True, default=False)
    acct_status = models.IntegerField(blank=True, default=0)
    lot_size = models.DecimalField(('lot_size'), max_digits=4, decimal_places=2, null=True, default=0.01, blank=True)
    payment_method = models.IntegerField(blank=True, default=0)
    acct_level = models.CharField(blank=True, max_length=12, null=True)
    acct_flags = models.CharField(blank=True, max_length=100, null=True)
    profit_2020_01 = models.DecimalField(('profit_2020_01'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_02 = models.DecimalField(('profit_2020_02'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_03 = models.DecimalField(('profit_2020_03'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_04 = models.DecimalField(('profit_2020_04'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_05 = models.DecimalField(('profit_2020_05'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_06 = models.DecimalField(('profit_2020_06'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_07 = models.DecimalField(('profit_2020_07'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_08 = models.DecimalField(('profit_2020_08'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_09 = models.DecimalField(('profit_2020_09'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_10 = models.DecimalField(('profit_2020_10'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_11 = models.DecimalField(('profit_2020_11'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2020_12 = models.DecimalField(('profit_2020_12'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_01 = models.DecimalField(('profit_2021_01'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_02 = models.DecimalField(('profit_2021_02'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_03 = models.DecimalField(('profit_2021_03'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_04 = models.DecimalField(('profit_2021_04'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_05 = models.DecimalField(('profit_2021_05'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_06 = models.DecimalField(('profit_2021_06'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_07 = models.DecimalField(('profit_2021_07'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_08 = models.DecimalField(('profit_2021_08'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_09 = models.DecimalField(('profit_2021_09'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_10 = models.DecimalField(('profit_2021_10'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_11 = models.DecimalField(('profit_2021_11'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    profit_2021_12 = models.DecimalField(('profit_2021_12'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    mt4_login = models.IntegerField(blank=True, default=0) # MT4 ACCOUNT NUMBER FROM BROKER
    mt4_title = models.CharField(blank=True, max_length=200) # NAME ON ACCOUNT
    mt4_last_balance = models.DecimalField(max_digits=19, decimal_places=8, null=True, default=0, blank=True)
    mt4_currency_code = models.CharField(blank=True, max_length=10)
    mt4_leverage = models.IntegerField(('mt4_leverage'), null=True, default=0, blank=True)
    mt4_DRAWDOWN = models.DecimalField(('mt4_DRAWDOWN'), max_digits=19, decimal_places=2, null=True, default=0, blank=True) # FLOAT
    mt4_DRAWDOWN_PCT = models.DecimalField(('mt4_DRAWDOWN_PCT'), max_digits=5, decimal_places=2, null=True, default=0, blank=True) 
    mt4_CLOSED_PNL = models.DecimalField(('mt4_CLOSED_PNL'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_used_mgn = models.DecimalField(('mt4_used_mgn'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_equity = models.DecimalField(('mt4_equity'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_free_margin = models.DecimalField(('mt4_free_margin'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_FREE_MARGIN_PCT = models.DecimalField(('mt4_FREE_MARGIN_PCT'), max_digits=18, decimal_places=2, null=True, default=0, blank=True)
    mt4_deposit = models.DecimalField(max_digits=21, decimal_places=8, null=True, default=0, blank=True)
    mt4_tx_count = models.DecimalField(('mt4_tx_count'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_last_status = models.IntegerField(blank=True, default=0)
    first_trade_ts = models.DateTimeField('first_trade_ts', null=True, blank=True)
    mt4_TOTAL_PROFIT_PCT = models.DecimalField(('mt4_TOTAL_PROFIT_PCT'), max_digits=7, decimal_places=2, null=True, default=0, blank=True)
    mt4_DAILY_PROFIT = models.DecimalField(('mt4_DAILY_PROFIT'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_DAILY_PROFIT_USD = models.DecimalField(('mt4_DAILY_PROFIT_USD'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_DAILY_PROFIT_PCT = models.DecimalField(('mt4_DAILY_PROFIT_PCT'), max_digits=4, decimal_places=2, null=True, default=0, blank=True)
    mt4_WEEKLY_PROFIT = models.DecimalField(('mt4_WEEKLY_PROFIT'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_WEEKLY_PROFIT_USD = models.DecimalField(('mt4_WEEKLY_PROFIT_USD'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_WEEKLY_PROFIT_PCT = models.DecimalField(('mt4_WEEKLY_PROFIT_PCT'), max_digits=4, decimal_places=2, null=True, default=0, blank=True)
    mt4_MONTHLY_PROFIT = models.DecimalField(('mt4_MONTHLY_PROFIT'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_MONTHLY_PROFIT_USD = models.DecimalField(('mt4_MONTHLY_PROFIT_USD'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_MONTHLY_PROFIT_PCT = models.DecimalField(('mt4_MONTHLY_PROFIT_PCT'), max_digits=4, decimal_places=2, null=True, default=0, blank=True)
    mt4_CLOSED_PNL_USD = models.DecimalField(('mt4_CLOSED_PNL_USD'), max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    mt4_last_balance_usd = models.DecimalField(max_digits=19, decimal_places=2, null=True, default=0, blank=True)
    profits_calculated_ts = models.DateTimeField(
        'profits_calculated_ts', null=True, blank=True)
    nickname = models.CharField(blank=True, null=True, max_length=20)

    def __str__(self):
        return str(self.skydesks_id) + " | " + str(self.nickname) + " " + str(self.mt4_CLOSED_PNL_USD)

    class Meta:
        db_table = 'MTConnection'

class HistoricalPrice(models.Model):
    currency_id = models.IntegerField(blank=True, default=0)
    td_currency_code = models.CharField(blank=True, max_length=10)
    currency_label = models.CharField(blank=True, max_length=200)
    created = models.DateField(auto_now_add=True, editable=False, null=False, blank=False)
    target_date = models.DateField(editable=True, null=True, blank=False)
    last_modified_ts = models.DateTimeField(auto_now=True, null=True, blank=True)
    last_modified_notes = models.CharField(null=True, blank=True, max_length=200)
    to_USD_value = models.DecimalField(('to_USD_value'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    def __str__(self):
        return str(self.currency_label)


class Invoice(models.Model):
    invoice_entry_num = models.IntegerField(blank=True, null=True)
    invoice_account = models.CharField(max_length=200)
    invoice_year_month = models.CharField(max_length=7, null=True, blank=True) # ex: 2021-06
    invoice_payee_id = models.ForeignKey(User, related_name='user_id', blank=True, default=3, on_delete=models.CASCADE)
    invoice_creation_date = models.DateField(blank=True, auto_now=True) # Lock in the currency rate on this date
    invoice_date_from = models.DateField(blank=True, default='2021-06-01')
    invoice_date_to = models.DateField(blank=True, default='2021-07-31')
    invoice_paid_on = models.DateTimeField(null=True, blank=True)
    invoice_notes = models.TextField(blank=True, max_length=255)
    td_base_currency_code = models.CharField(max_length=20, default="BTC/USD") # Twelvedata td_currency_code eg. BTC/USD
    invoice_total_BTC = models.DecimalField(('invoice_total_BTC'), max_digits=19, decimal_places=8, null=True, default=0, blank=True)
    invoice_total_USD = models.DecimalField(('invoice_total_USD'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    invoice_total_CAD = models.DecimalField(('invoice_total_CAD'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    invoice_total_ETH = models.DecimalField(('invoice_total_ETH'), max_digits=32, decimal_places=18, null=True, default=0, blank=True)
    invoice_total_EUR = models.DecimalField(('invoice_total_EUR'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    invoice_total_XRP = models.DecimalField(('invoice_total_XRP'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    invoice_total_LTC = models.DecimalField(('invoice_total_LTC'), max_digits=19, decimal_places=5, null=True, default=0, blank=True)
    invoice_credit_used = models.DecimalField(('invoice_credit_used'), max_digits=19, decimal_places=8, null=True, default=0, blank=True)
    invoice_payment_url = models.URLField(null=True, blank=True)
    btc_deposit_address = models.CharField(max_length=35, blank=True, null=True, unique=False) # 26-35 chars to support legacy and segwit
    bits_outstanding_balance = models.DecimalField(('bits_outstanding_balance'), max_digits=19, decimal_places=8, null=True, default=0, blank=True)
    bits_confirmed_balance = models.DecimalField(('bits_confirmed_balance'), max_digits=19, decimal_places=8, null=True, default=0, blank=True)
    is_paid = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False) # Mark true when it's ready for distribution
    is_void = models.BooleanField(default=False)
    subscription_length = models.IntegerField(null=True, default=0) # 0 is monthly, 1 meaning half year, 2 is annual
    discount_pct = models.IntegerField('discount', null=True, default=0)
    invoice_type = models.IntegerField(blank=True, default=0) # 0 is subscription, 1 is revshare, 2 is sales rep, 3 is whitelabel
    has_negative_accounts = models.BooleanField(null=True,blank=True,default=False)
    made_zero_profit =  models.BooleanField(null=True,blank=True,default=False)

    def __str__(self):
        return str(self.invoice_payee_id) + " | " + str(self.invoice_creation_date) + " " + str(self.invoice_total_USD) +" " + str(self.td_base_currency_code)

class InvoiceItem(models.Model):
    invoice_parent = models.IntegerField(blank=True, default=0, null=True)
    product_title = models.CharField(max_length=200, blank=True, null=True)
    code = models.CharField(max_length=200, null=True, blank=True)
    price = models.DecimalField(max_digits=19, decimal_places=5, null=True, blank=True)
    currency_code = models.CharField(max_length=34, blank=True, null=True, unique=False, default="USD")
    td_base_currency_code = models.CharField(max_length=20,null=True, blank=True) # Twelvedata td_currency_code eg. BTC/USD
    BTC_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True) # Converted using HistoricalPrice
    USD_price = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) # Converted using HistoricalPrice
    CAD_price = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) # Converted using HistoricalPrice
    ETH_price = models.DecimalField(max_digits=19, decimal_places=18, null=True, blank=True) # Converted using HistoricalPrice
    LTC_price = models.DecimalField(max_digits=19, decimal_places=8, null=True, blank=True) # Converted using HistoricalPrice
    XRP_price = models.DecimalField(max_digits=19, decimal_places=6, null=True, blank=True) # Converted using HistoricalPrice
    quantity = models.IntegerField(default=1, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'InvoiceItem'

    def __str__(self):
        return str(self.product_title) + " | " + str(self.price) 

# `notification_type` 1 is invoice, 2 is lot size change, 3 is mt4 credentials update, 4 is wallet withdrawal, 5 is account balance related, 6 is credentials change, 7 is other
class NotificationItem(models.Model):
    user_id = models.IntegerField(blank=True, default=0, null=True)
    related_id = models.IntegerField(blank=True, default=0, null=True) # If there is a parent notification
    notification_type = models.IntegerField(blank=True, default=0, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_hidden = models.BooleanField(default=False)
    dismissed_on = models.DateTimeField(null=True, blank=True)
    processed_on = models.DateTimeField(null=True, blank=True)
    priority_level = models.IntegerField(blank=True, default=0, null=True)
    notification_details = models.CharField(max_length=255, null=True, blank=True)
    notification_title = models.CharField(max_length=100, null=True, blank=True)
    config_1 = models.CharField(max_length=200, null=True, blank=True)
    config_2 = models.CharField(max_length=200, null=True, blank=True)
    config_3 = models.CharField(max_length=200, null=True, blank=True)
    config_4 = models.CharField(max_length=200, null=True, blank=True)
    is_viewed = models.BooleanField(default=False, blank=True)