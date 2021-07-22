from django.core.files.storage import default_storage
from rest_framework import generics, mixins
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from admin.pagination import CustomPagination
from users.models import User, Referral
from products.models import Product, MTConnection, HistoricalPrice, Invoice, InvoiceItem, NotificationItem
from products.serializers import ProductSerializer, MTCSerializer, InvoiceSerializer, InvoiceItemSerializer, NotificationItemSerializer
from users.authentication import JWTAuthentication
from django.http.response import HttpResponse
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.decorators import api_view
import pickle, json
from decimal import *
try:  # Python 3+
    from urllib.parse import (
        parse_qs, parse_qsl, urlencode, urlparse, urlunparse
    )
except ImportError:  # Python 2
    from urllib import urlencode
    from urlparse import parse_qs, parse_qsl, urlparse, urlunparse

API_URL = 'http://domain.com:8000/api/'

@api_view(['GET', 'POST', ])
def qrcode(request, btc_address, amount):
    print("BTC", btc_address, amount)
    qr_output_text = "bitcoin:" + btc_address + "?amount=" + amount + "&label="
    import pyqrcode
    import io
    url = pyqrcode.create(qr_output_text)
    buffer = io.BytesIO() # in-memory stream is also supported
    url.svg(buffer, scale=8)
    return Response(buffer.getvalue())

def provision_ftp(connection_id, mt4_login):
    host = 'domain.com'
    user = 'all'
    passwd = 'hunter2'
    import ftplib
    ftp = ftplib.FTP(host)
    ftp.set_pasv(True)
    ftp.login(user, passwd)
    connection_id = str(connection_id)
    if connection_id in ftp.nlst():
        print("FTP FOLDER OK")
    else:
        print('MKDIR FTP ')
        ftp.mkd(connection_id)
        ftp.cwd(connection_id)
    ftp.quit()

    import json, requests
    sd_url = 'https://api.domain.com/v2/subscriptions/' + str(connection_id) + '/actions/options/ftp'
    h = {  
        'Authorization': 'Bearer hunter2',
    }
    data = {
        'accept': 'application/json',
        'callback_url':'http://domain.com:8000/api/update',
        'server_name': 'domain.com',
        'path': str(connection_id),
        'username':'all',
        'password':'hunter2',
        'account': mt4_login
    }
    sd_resp = requests.post(sd_url, headers=h, data=data).content.decode('utf-8')
    sd_resp_json = json.loads(sd_resp)
    print(sd_resp_json)

class payment_amount(APIView):
    """
    Submit a BTC address that already uniquely corresponds to a user and returns their expected balance for payment confirmation
    """
    def post(self, request):
        import json
        try: # Find which user this address belongs to
            btc_address = self.request.query_params.get('btc_address')
            user = User.objects.get(btc_deposit_address=btc_address)
            data = {
                'btc_address': btc_address,
                'outstanding_balance':  user.BTC_outstanding_balance,
                'BTC_confirmed_balance': user.BTC_confirmed_balance
            }
        except:
            return Response("Invalid Address")
        return Response(data)

class paid(APIView):
    """
    Submit a BTC address that already uniquely corresponds to a user and returns their expected balance for payment confirmation
    """
    def post(self, request):
        from django.utils.timezone import now
        import json, requests
        import redis # Query redis for this address
        btc_address = self.request.query_params.get('btc_address')
        user = User.objects.get(btc_deposit_address=btc_address)
        # Is this user initialized?
        CURRENT_INVOICE_ID = user.current_invoice_id
        if (CURRENT_INVOICE_ID != '' and CURRENT_INVOICE_ID != None and CURRENT_INVOICE_ID > 0 ): # Valid invoice
            c_invoice = Invoice.objects.get(pk=CURRENT_INVOICE_ID)
            INV_ACCT = c_invoice.invoice_account
            # Get the balance OWING
            BALANCE_OWING = Decimal(user.BTC_outstanding_balance)
            # Get the user's credit if they overpaid previously
            BALANCE_CREDIT = Decimal(user.btc_credit)
            # Summary to double check
            print(f'I1#: {CURRENT_INVOICE_ID} PAID? {c_invoice.is_paid} {user.first_name} OWES {BALANCE_OWING} BTC_CREDIT: {BALANCE_CREDIT}')
            # Does this user need to pay?
            if (BALANCE_OWING > 0):
                # Is there enough to cover the invoice?
                INVOICE_OWING = BALANCE_CREDIT - BALANCE_OWING
                if (c_invoice.is_paid == False): # Is this invoice paid?
                    n_title = "Invoice has been paid!"
                    n_details = "Thank you for your payment"
                    print(f'{user.current_invoice_id} InvOwe: {INVOICE_OWING}') # including credit

                    if (INVOICE_OWING == 0):
                        print("exact! using only btc_credit")
                        user.btc_credit = 0
                        user.last_invoice_amount = BALANCE_OWING
                        btc_invoices_paid = BALANCE_OWING + Decimal(user.btc_invoices_paid)
                        user.btc_invoices_paid = btc_invoices_paid
                        c_invoice.is_paid = True
                        c_invoice.BTC_confirmed_balance = BALANCE_OWING
                        c_invoice.invoice_paid_on = now()
                        n_item = NotificationItem(user_id=user.id, notification_type=1, priority_level=2, notification_title=n_title, notification_details=n_details, config_1=BALANCE_OWING, config_2=c_invoice.td_base_currency_code, config_3=INV_ACCT, config_4=CURRENT_INVOICE_ID)
                        n_item.save()
                        BALANCE_OWING = 0
                        user.BTC_outstanding_balance = 0
                        user.save()
                        c_invoice.save()
                        data = {
                            'status': 'PAID',
                            'btc_address': btc_address,
                            'outstanding_balance': 0,
                            'tx_id': user.last_btc_tx_hash,
                        }   

                        if (INV_ACCT == 'S00' or INV_ACCT == 'S01' or INV_ACCT == 'S02'):
                            SD_ID = c_invoice.connection_id
                            print("SUB_INVID:", CURRENT_INVOICE_ID, "SID2:", SD_ID)
                            if (SD_ID == 0): # Didn't create subscription? Do it then
                                c2_invoice = Invoice.objects.get(id=CURRENT_INVOICE_ID)
                                _resp_url = 'http://localhost:8000/api/new?id=' + str(user.id)
                                sd_new_resp = requests.post(_resp_url)
                                sd_new_json = json.loads(sd_new_resp.content.decode('utf-8'))
                                connection_id = sd_new_json['connection_id']
                                # Now we select our invoice and credit them with a connection_id
                                c2_invoice.connection_id = connection_id
                                c2_invoice.save()
                            data = {
                                'status': 'PAID',
                                'btc_address': btc_address,
                                'tx_id': user.last_btc_tx_hash,
                                'connection_id' : SD_ID
                            }
                            return Response(data)

                        return Response(data)

                    if (INVOICE_OWING) > 0: # Can successfully pay with credit
                        print("Pay with btc_credit")
                        user.btc_credit = INVOICE_OWING
                        user.last_invoice_amount = BALANCE_OWING
                        btc_invoices_paid = BALANCE_OWING + Decimal(user.btc_invoices_paid)
                        user.btc_invoices_paid = btc_invoices_paid
                        c_invoice.is_paid = True
                        c_invoice.BTC_confirmed_balance = BALANCE_OWING
                        c_invoice.invoice_paid_on = now()
                        n_item = NotificationItem(user_id=user.id, notification_type=1, priority_level=2, notification_title=n_title, notification_details=n_details, config_1=BALANCE_OWING, config_2=c_invoice.td_base_currency_code, config_3=INV_ACCT)
                        n_item.save()
                        BALANCE_OWING = 0
                        user.BTC_outstanding_balance = 0
                        user.save()
                        c_invoice.save()

                        data = {
                            'status': 'PAID',
                            'btc_address': btc_address,
                            'outstanding_balance': 0,
                            'tx_id': user.last_btc_tx_hash,
                        }
                        return Response(data)

                    if (INVOICE_OWING < 0): # Incomplete payment, OWING amount is NEGATIVE
                        BTC_INVOICES_PAID = Decimal(user.btc_invoices_paid)
                        print(f'PREV BTC_INVOICES_PAID: {BTC_INVOICES_PAID}')
                        # First check if there were any fresh transactions
                        r = redis.Redis(host='domain.com', port=31482, password='hunter2', db=0, decode_responses=True)
                        try:
                            LAST_UPDATED = r.get("l_" + btc_address)
                            last_btc_tx_hash = r.get("t_" + btc_address)
                        except:
                            print("lu and tx fail")
                        try: # Get history
                            res = requests.get('https://block.io/api/v2/get_address_balance/?api_key=hunter2&addresses=' + str(btc_address)).content.decode('utf-8')
                            bio_resp_json = json.loads(res)
                            AVAILABLE_BALANCE = Decimal(bio_resp_json['data']['available_balance'])
                            pending_rcv_bal = Decimal(bio_resp_json['data']['pending_received_balance'])
                            user.BTC_confirmed_balance = AVAILABLE_BALANCE
                            print(f'BIO BAL:{AVAILABLE_BALANCE} RCV: {pending_rcv_bal}')

                            # SECONDARY CALCULATION INCLUDING RUNNING TOTAL BTC_INVOICES_PAID
                            INVOICE_REMAINDER = AVAILABLE_BALANCE - abs(INVOICE_OWING) - BTC_INVOICES_PAID
                            print("STAGE2: REMAIN:", INVOICE_REMAINDER) # NEGATIVE MEANS NOT ENOUGH

                            # EAGER SETTLEMENT
                            if (pending_rcv_bal == abs(INVOICE_REMAINDER)):
                                c_invoice.is_paid = True
                                c_invoice.notes = "PAID EXACTLY"
                                c_invoice.BTC_confirmed_balance = BALANCE_OWING
                                c_invoice.invoice_paid_on = now()
                                n_item = NotificationItem(user_id=user.id, notification_type=1, priority_level=2, notification_title=n_title, notification_details=n_details, config_1=BALANCE_OWING, config_2=c_invoice.td_base_currency_code, config_3=INV_ACCT)
                                n_item.save()
                                user.BTC_outstanding_balance = 0
                                user.btc_credit = 0
                                user.last_invoice_amount = BALANCE_OWING
                                user.last_btc_tx_hash = last_btc_tx_hash
                                updated_btc_invoices_paid = BALANCE_OWING + Decimal(user.btc_invoices_paid)
                                user.btc_invoices_paid = updated_btc_invoices_paid
                                user.save()
                                c_invoice.save()

                            if (INVOICE_REMAINDER < 0): # still owe
                                qr_output_text = "bitcoin:" + btc_address + "?amount=" + str(abs(INVOICE_REMAINDER)) + "&label="
                                import pyqrcode
                                import io
                                url = pyqrcode.create(qr_output_text)
                                buffer = io.BytesIO() # in-memory stream is also supported
                                url.svg(buffer, scale=5)
                                qr_new = buffer.getvalue()
                                data = {
                                    'status': 'WAITING FOR PAYMENT',
                                    'btc_address': btc_address,
                                    'outstanding_balance': str(abs(INVOICE_REMAINDER)),
                                    'qr_svg': qr_new,
                                } 
                                return Response(data)
                            if (INVOICE_REMAINDER > 0): # PAID WITH EXTRA
                                user.btc_credit = INVOICE_REMAINDER
                                user.last_invoice_amount = BALANCE_OWING
                                btc_invoices_paid = BALANCE_OWING + Decimal(user.btc_invoices_paid)
                                user.btc_invoices_paid = btc_invoices_paid
                                c_invoice.is_paid = True
                                c_invoice.BTC_confirmed_balance = BALANCE_OWING
                                c_invoice.invoice_paid_on = now()
                                n_item = NotificationItem(user_id=user.id, notification_type=1, priority_level=2, notification_title=n_title, notification_details=n_details, config_1=BALANCE_OWING, config_2=c_invoice.td_base_currency_code, config_3=INV_ACCT)
                                n_item.save()

                                BALANCE_OWING = 0
                                user.BTC_outstanding_balance = 0
                                user.save()
                                c_invoice.save()

                                data = {
                                    'status': 'PAID',
                                    'btc_address': btc_address,
                                    'outstanding_balance': 0,
                                    'tx_id': user.last_btc_tx_hash,
                                }

                                if (INV_ACCT == 'S00' or INV_ACCT == 'S01' or INV_ACCT == 'S02'):
                                    SD_ID = c_invoice.connection_id
                                    print("SUB_INVID:", CURRENT_INVOICE_ID, "SID2:", SD_ID)
                                    if (SD_ID == 0):
                                        c2_invoice = Invoice.objects.get(id=CURRENT_INVOICE_ID)
                                        _resp_url = 'http://localhost:8000/api/new?id=' + str(user.id)
                                        sd_new_resp = requests.post(_resp_url)
                                        sd_new_json = json.loads(sd_new_resp.content.decode('utf-8'))
                                        connection_id = sd_new_json['connection_id']
                                        # Now we select our invoice and credit them with a connection_id
                                        c2_invoice.connection_id = connection_id
                                        SD_ID = c2_invoice.connection_id
                                        c2_invoice.invoice_paid_on = now()
                                        c2_invoice.save()
                                    data = {
                                        'status': 'PAID',
                                        'btc_address': btc_address,
                                        'outstanding_balance': 0,
                                        'tx_id': user.last_btc_tx_hash,
                                        'connection_id' : SD_ID
                                    }
                                    return Response(data)
                                return Response(data)

                        except:
                            print("Block.IO error", res.content.decode('utf-8'))

                    qr_output_text = "bitcoin:" + btc_address + "?amount=" + str(abs(INVOICE_OWING)) + "&label="
                    import pyqrcode
                    import io
                    url = pyqrcode.create(qr_output_text)
                    buffer = io.BytesIO() # in-memory stream is also supported
                    url.svg(buffer, scale=5) # do whatever you want with buffer.getvalue()
                    qr_new = buffer.getvalue()
                    data = {
                        'status': 'WAITING FOR PAYMENT',
                        'btc_address': btc_address,
                        'outstanding_balance': str(abs(INVOICE_OWING)),
                        'qr_svg': qr_new,
                    }
                    return Response(data)

        # Double check what we did
        print(f'I2#: {CURRENT_INVOICE_ID} PAID? {c_invoice.is_paid} {user.first_name} OWES {BALANCE_OWING} BTC_CREDIT: {user.btc_credit}')
        if (c_invoice.is_paid == True):
            if (INV_ACCT == 'S00' or INV_ACCT == 'S01' or INV_ACCT == 'S02'):
                try:
                    import time, datetime
                    from datetime import datetime, timedelta
                    # CHECK IF USER used up their referral credit
                    u_ref = User.objects.get(id=user.id)
                    if (u_ref.referral_credit_used == False):
                        # Give a referral credit to the referrer in 30 days
                        REFERRAL_PARENT = u_ref.referral_parent
                        print("PARENT2", REFERRAL_PARENT)
                        today_date = datetime.now()
                        td = today_date + timedelta(days=30)
                        parent_user = User.objects.get(id=REFERRAL_PARENT)
                        print("TRY REF3", parent_user.id, td, today_date, parent_user.id)
                        try:  # Calculate the $20 reward at current market rate
                            print("GETTING BTC FX")
                            BTC_USD = requests.post('http://domain.com:8000/api/fx/BTC_USD').content.decode('utf-8')
                            BTC_USD = Decimal(BTC_USD[1:-1]) # remove the quotes
                            bonus_credit_bits = round((20 / BTC_USD)*1000000, 0)
                            print("CREDIT IN 30 DAYS:", td, bonus_credit_bits, "bits @ ", BTC_USD)
                            print(u_ref.id, "->", parent_user.id)
                            referral = Referral(referral_from_user=u_ref, referral_to_user=parent_user, referral_registered=today_date, referral_type=1, referral_amount_bits=bonus_credit_bits,credited_on=td)
                            referral.save()
                            print("REF_OK")
                            u_ref.user_funnel_step = 41
                            u_ref.referral_credit_used = 1
                            u_ref.save()
                        except:
                            print("failed to credit referral", u_ref.id)
                except:
                    print('Referral fail', CURRENT_INVOICE_ID)

                SD_ID = c_invoice.connection_id
                print("SUB_INVID:", CURRENT_INVOICE_ID, "SID2:", SD_ID)
                if (SD_ID == 0): # didn't create subscription for some reason
                    c2_invoice = Invoice.objects.get(id=CURRENT_INVOICE_ID)
                    print("making new2", c2_invoice.connection_id, user.id)
                    _resp_url = 'http://localhost:8000/api/new?id=' + str(user.id)
                    sd_new_resp = requests.post(_resp_url)
                    sd_new_json = json.loads(sd_new_resp.content.decode('utf-8'))
                    connection_id = sd_new_json['connection_id']
                    # Now we select our invoice and credit them with a connection_id
                    c2_invoice.connection_id = connection_id
                    c2_invoice.save()
                data = {
                    'status': 'PAID',
                    'btc_address': btc_address,
                    'outstanding_balance': 0,
                    'tx_id': user.last_btc_tx_hash,
                    'connection_id' : SD_ID
                }
                return Response(data)

            data = {
                'status': 'PAID',
                'btc_address': btc_address,
                'outstanding_balance': 0,
                'tx_id': user.last_btc_tx_hash,
            }
            return Response(data)

        data = {
                'status': 'WAITING FOR PAYMENT',
                'btc_address': btc_address,
                'outstanding_balance': BALANCE_OWING,
        }

        return Response(data)

def get_query_field(url, field):
    """
    Given a URL, return a list of values for the given ``field`` in the
    URL's query string.
    
    >>> get_query_field('http://example.net', field='foo')
    []
    
    >>> get_query_field('http://example.net?foo=bar', field='foo')
    ['bar']
    
    >>> get_query_field('http://example.net?foo=bar&foo=baz', field='foo')
    ['bar', 'baz']
    """
    try:
        return parse_qs(urlparse(url).query)[field]
    except KeyError:
        return []

class MTCGenericAPIView( generics.GenericAPIView, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin):
    """
    Returns all MTConnections and provides GET, POST, and PUT
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = MTConnection.objects.all().order_by('created')
    serializer_class = MTCSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return MTConnection.objects.all()

    def get(self, request, pk=None):
        queryset2 = MTConnection.objects.filter(acct_owner_id=request.user.id).order_by('created')
        if pk:
            return Response({
                'data': self.retrieve(request, pk).data
            })
        if request.user.role.id == 1:
            return self.list(request)
        else:
            print(request.user.email, "MTC Unauthorized!")
            return Response("Unauthorized!") 

    def post(self, request):
        if request.user.role.id == 1:
            return Response({
                'data': self.create(request).data
            })
        else:
            print(request.user.email, "MTC Unauthorized!")
            return Response("Unauthorized!") 

    def put(self, request, pk=None):
        if request.user.role.id == 1:
            return Response({
                'data': self.partial_update(request, pk).data
            })
        else:
            print(request.user.email, "MTC Unauthorized!")
            return Response("Unauthorized!") 

    def delete(self, request, pk=None):
        if request.user.role.id == 1:
            return self.destroy(request, pk)
        else:
            print(request.user.email, "MTC Unauthorized!")
            return Response("Unauthorized!")  

class MTCList(generics.ListAPIView):
    """
    Looks up the MTConnection based on the connection_id
    """
    serializer_class = MTCSerializer

    def get_queryset(self):
        queryset = MTConnection.objects.all().order_by('-created')
        connection_id = self.request.query_params.get('id')
        if connection_id is not None:
            queryset = queryset.filter(connection_id=connection_id)[::-1]
        return queryset[:1] # Return only the latest record in case of duplicates

class get_id(APIView):
    """
    Accepts a connection ID as a url param returns the PK ID for subsequent PUT updates
    """
    def get(self, request, pk=None):
        try:
            if pk:
                db_pk = MTConnection.objects.get(connection_id=pk)
            return HttpResponse(db_pk.id)
        except:
            return HttpResponse(0)

class redisgod(APIView):
    """
    Triggers Redis FX update if '/update' or returns supported FX pair as a string
    """
    def post(self, request, fx_pair=None):
        import json
        import urllib.parse
        import time
        try: # Parse incoming data if any
            import redis
            r = redis.Redis(host='domain.com', port=31482, password='hunter2', db=0, decode_responses=True)
            if (fx_pair == 'update'):
                try: # Connect with TwelveData API
                    import requests
                    td_res = requests.get('https://api.twelvedata.com/time_series?symbol=LTC/USD,CAD/USD,BTC/USD,ETH/USD,XRP/USD,BRL/USD,GBP/USD,EUR/USD,CNY/USD,HKD/USD,INR/USD,RUB/USD,SGD/USD,JPY/USD,KRW/USD,AUD/USD,NZD/USD,TRY/USD,DKK/USD,MXN/USD,NOK/USD,ISL/USD,THB/USD,BCH/USD&interval=1min&outputsize=1&apikey=hunter2')
                    td_fx = td_res.json()
                    r.set('BTC__USD', td_fx['BTC/USD']['values'][0]['close'])
                    r.set('BCH__USD', td_fx['BCH/USD']['values'][0]['close'])
                    r.set('LTC__USD', td_fx['LTC/USD']['values'][0]['close'])
                    r.set('ETH__USD', td_fx['ETH/USD']['values'][0]['close'])
                    r.set('CAD__USD', td_fx['CAD/USD']['values'][0]['close'])
                    r.set('XRP__USD', td_fx['XRP/USD']['values'][0]['close'])
                    r.set('BRL__USD', td_fx['BRL/USD']['values'][0]['close'])
                    r.set('GBP__USD', td_fx['GBP/USD']['values'][0]['close'])
                    r.set('EUR__USD', td_fx['EUR/USD']['values'][0]['close'])
                    r.set('CNY__USD', td_fx['CNY/USD']['values'][0]['close'])
                    r.set('HKD__USD', td_fx['HKD/USD']['values'][0]['close'])
                    r.set('INR__USD', td_fx['INR/USD']['values'][0]['close'])
                    r.set('RUB__USD', td_fx['RUB/USD']['values'][0]['close'])
                    r.set('SGD__USD', td_fx['SGD/USD']['values'][0]['close'])
                    r.set('JPY__USD', td_fx['JPY/USD']['values'][0]['close'])
                    r.set('KRW__USD', td_fx['KRW/USD']['values'][0]['close'])
                    r.set('AUD__USD', td_fx['AUD/USD']['values'][0]['close'])
                    r.set('NZD__USD', td_fx['NZD/USD']['values'][0]['close'])
                    r.set('TRY__USD', td_fx['TRY/USD']['values'][0]['close'])
                    r.set('DKK__USD', td_fx['DKK/USD']['values'][0]['close'])
                    r.set('MXN__USD', td_fx['MXN/USD']['values'][0]['close'])
                    r.set('NOK__USD', td_fx['NOK/USD']['values'][0]['close'])
                    r.set('ISL__USD', td_fx['ISL/USD']['values'][0]['close'])
                    r.set('THB__USD', td_fx['THB/USD']['values'][0]['close'])
                except:
                    return Response("12Data fail")
            
            # Go and get it
            BTC_USD = r.get('BTC__USD')
            BCH_USD = r.get('BCH__USD')
            LTC_USD = r.get('LTC__USD')
            ETH_USD = r.get('ETH__USD')
            CAD_USD = r.get('CAD__USD')
            XRP_USD = r.get('XRP__USD')
            BRL_USD = r.get('BRL__USD')
            GBP_USD = r.get('GBP__USD')
            EUR_USD = r.get('EUR__USD')
            CNY_USD = r.get('CNY__USD')
            HKD_USD = r.get('HKD__USD')
            INR_USD = r.get('INR__USD')
            RUB_USD = r.get('RUB__USD')
            SGD_USD = r.get('SGD__USD')
            JPY_USD = r.get('JPY__USD')
            KRW_USD = r.get('KRW__USD')
            AUD_USD = r.get('AUD__USD')
            NZD_USD = r.get('NZD__USD')
            TRY_USD = r.get('TRY__USD')
            DKK_USD = r.get('DKK__USD')
            MXN_USD = r.get('MXN__USD')
            NOK_USD = r.get('NOK__USD')
            NOK_USD = r.get('NOK__USD')
            ISL_USD = r.get('ISL__USD')
            THB_USD = r.get('THB__USD')

            if (fx_pair == 'BTC_USD'): return Response(BTC_USD)
            if (fx_pair == 'BCH_USD'): return Response(BCH_USD)
            if (fx_pair == 'LTC_USD'): return Response(LTC_USD)
            if (fx_pair == 'ETH_USD'): return Response(ETH_USD)
            if (fx_pair == 'CAD_USD'): return Response(CAD_USD)
            if (fx_pair == 'XRP_USD'): return Response(XRP_USD)
            if (fx_pair == 'BRL_USD'): return Response(BRL_USD)
            if (fx_pair == 'GBP_USD'): return Response(GBP_USD)
            if (fx_pair == 'EUR_USD'): return Response(EUR_USD)
            if (fx_pair == 'CNY_USD'): return Response(CNY_USD)
            if (fx_pair == 'HKD_USD'): return Response(HKD_USD)
            if (fx_pair == 'INR_USD'): return Response(INR_USD)
            if (fx_pair == 'RUB_USD'): return Response(RUB_USD)
            if (fx_pair == 'SGD_USD'): return Response(SGD_USD)
            if (fx_pair == 'JPY_USD'): return Response(JPY_USD)
            if (fx_pair == 'KRW_USD'): return Response(KRW_USD)
            if (fx_pair == 'AUD_USD'): return Response(AUD_USD)
            if (fx_pair == 'NZD_USD'): return Response(NZD_USD)
            if (fx_pair == 'TRY_USD'): return Response(TRY_USD)
            if (fx_pair == 'DKK_USD'): return Response(DKK_USD)
            if (fx_pair == 'MXN_USD'): return Response(MXN_USD)
            if (fx_pair == 'NOK_USD'): return Response(NOK_USD)
            if (fx_pair == 'ISL_USD'): return Response(ISL_USD)
            if (fx_pair == 'THB_USD'): return Response(THB_USD)
            
            data = { # If no parameters were provided
                'BCH_USD': BCH_USD, 
                'BTC_USD': BTC_USD,
                'LTC_USD': LTC_USD,
                'ETH_USD': ETH_USD,
                'CAD_USD': CAD_USD,
                'XRP_USD': XRP_USD,
                'BRL_USD': BRL_USD,
                'GBP_USD': GBP_USD,
                'EUR_USD': EUR_USD,
                'CNY_USD': CNY_USD,
                'HKD_USD': HKD_USD,
                'INR_USD': INR_USD,
                'RUB_USD': RUB_USD,
                'SGD_USD': SGD_USD,
                'JPY_USD': JPY_USD,
                'KRW_USD': KRW_USD,
                'AUD_USD': AUD_USD,
                'NZD_USD': NZD_USD,
                'TRY_USD': TRY_USD,
                'DKK_USD': DKK_USD,
                'MXN_USD': MXN_USD,
                'NOK_USD': NOK_USD,
                'NOK_USD': NOK_USD,
                'ISL_USD': ISL_USD,
                'THB_USD': THB_USD
            }
            return Response(data)  
        except:
            return Response("Redis fail")

class ProductGenericAPIView(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin
):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = CustomPagination

    def get(self, request, pk=None):
        if pk:
            return Response({
                'data': self.retrieve(request, pk).data
            })

        return self.list(request)

    def post(self, request):
        return Response({
            'data': self.create(request).data
        })

    def put(self, request, pk=None):
        return Response({
            'data': self.partial_update(request, pk).data
        })

    def delete(self, request, pk=None):
        return self.destroy(request, pk)
class FileUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,)

    def post(self, request):
        file = request.FILES['image']
        file_name = default_storage.save(file.name, file)
        url = default_storage.url(file_name)

        return Response({
            'url': 'http://localhost:8000/api' + url
        })

        
class InvoiceGenericAPIView(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin
):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Invoice.objects.all().order_by('id')
    serializer_class = InvoiceSerializer
    pagination_class = CustomPagination

    def get(self, request, pk=None):
        from django.forms.models import model_to_dict
        queryset4 = InvoiceItem.objects.filter(invoice_parent=pk)
        details = InvoiceItemSerializer(queryset4, many=True).data
        pkl = pickle.loads(pickle.dumps(queryset4))
        if (request.GET.get('action') == 'update'):
            from decimal import Decimal
            import redis
            r = redis.Redis(host='domain.com', port=31482, password='hunter2', db=0, decode_responses=True)
            BTC_TOTAL = 0
            CAD_TOTAL = 0
            ETH_TOTAL = 0
            USD_TOTAL = 0
            invoice_items = 0
            for i in queryset4:
                print(i.currency_code, i.price)
                if i.currency_code == 'USD': # USD TO CAD AND BTC AND ETH
                    i.BTC_price = round(Decimal(i.price) / Decimal(r.get('BTC__USD')), 8)
                    i.ETH_price = round(Decimal(i.price) / Decimal(r.get('ETH__USD')), 18)
                    i.CAD_price = round(Decimal(i.price) / Decimal(r.get('CAD__USD')), 2)
                    i.LTC_price = round(Decimal(i.price) / Decimal(r.get('LTC__USD')), 8)
                    i.XRP_price = round(Decimal(i.price) / Decimal(r.get('XRP__USD')), 6)
                    i.USD_price = i.price # 1:1 mapping 
                    BTC_TOTAL += Decimal(i.BTC_price) 
                    CAD_TOTAL += Decimal(i.CAD_price) 
                    ETH_TOTAL += Decimal(i.ETH_price) 
                    USD_TOTAL += Decimal(i.USD_price) 
                i.save()
                invoice_items += 1
        
            # Calculate totals
            print("INV #", pk)
            print(invoice_items, "items | ", BTC_TOTAL, "BTC | ", CAD_TOTAL, "CAD | ",  USD_TOTAL, "USD")
            # Update the parent invoice pk
            if pk:
                master_invoice =Invoice.objects.get(id=pk)
                master_invoice.invoice_total_BTC = BTC_TOTAL
                master_invoice.invoice_total_CAD = CAD_TOTAL
                master_invoice.invoice_total_USD = USD_TOTAL
                master_invoice.invoice_total_CAD = CAD_TOTAL
                master_invoice.save()
                print(master_invoice)

        if pk:
            return Response({
                'data': self.retrieve(request, pk).data,
                'details': details
            })

        if request.user.role.id == 1:
            return self.list(request)
        else:
            print(request.user.email, request.user.role, "INVOICE_DENIED")
            return Response("Unauthorized!" ) 

        # return self.list(request)

    def post(self, request):
        import time
        new_invoice = json.loads(request.body.decode('utf-8')) # Load in the JSON request
        INVOICE_ENTRY_TS = int(time.time())
        NEG_FLAG = False
        # The master address in case of failures
        btc_deposit_address = '3B16kRBKdNYkrjHmc98Yjux8wDehu23b9B'
        INVOICE_ACCOUNT = new_invoice['invoice_account']
        try: REQ_PRICE = new_invoice['price']
        except: REQ_PRICE = 0.89

        REQ_CURRENCY_CODE = new_invoice['currency_code']
        try: invoice_credit_used = Decimal(new_invoice['invoice_credit_used'])
        except: invoice_credit_used = 0
        try: invoice_year_month = new_invoice['invoice_year_month']
        except: invoice_year_month = '2020_11' # DEFAULT IF NO MONTH GIVEN
        try: # see if this works
            if request.user.id:
                btc_deposit_address = request.user.btc_deposit_address
                print("USR:", request.user.id, "BTC ADDR:", btc_deposit_address)
                if (btc_deposit_address == None or btc_deposit_address == ''):
                    print("CREATING BTC ADDR FOR ", request.user.id)
                    try:
                        import requests
                        res = requests.get('https://block.io/api/v2/get_new_address/?api_key=hunter2&label=' + str(request.user.id))
                        bio_resp = res.content.decode('utf-8')
                        print(bio_resp)
                        if "fail" in bio_resp: # Already exists, get the id associated with the pk
                            res = requests.get('https://block.io/api/v2/get_address_by_label/?api_key=hunter2&label=' + str(request.user.id))
                            print(res.content.decode('utf-8'))
                            addy_resp = json.loads(res.content.decode('utf-8'))
                            bio_address = addy_resp['data']['address']
                            btc_deposit_address = addy_resp['data']['address']
                            try: # Update the user BTC deposit address
                                from users.models import User
                                user = User.objects.get(pk=request.user.id)
                                user.btc_deposit_address = btc_deposit_address
                                user.save()
                                print("RECOVERED ", user.email, "BTC", btc_deposit_address)
                            except:
                                print("btc address set fail using fallback")
                                btc_deposit_address = '3B16kRBKdNYkrjHmc98Yjux8wDehu23b9B'
                        if "success" in bio_resp:
                            bio_resp_json = json.loads(bio_resp)
                            bio_address = bio_resp_json['data']['address']
                            btc_deposit_address = bio_address
                            from users.models import User
                            user = User.objects.get(pk=request.user.id)
                            user.btc_deposit_address = bio_address
                            user.save()

                        try: # Initialize this BTC address with external API
                            res = requests.get('http://domain.com:7373/btc/' + str(btc_deposit_address))
                            print(res.content.decode("utf-8"))
                        except:
                            print("BTC Payment API fail :'(")
                    except:
                        print("Failed to create new address, using fallback")
        except: pass
        # Currency conversion through Redis
        import redis
        r = redis.Redis(host='domain.com', port=31482, password='hunter2', db=0, decode_responses=True)    
        BTC_USD = r.get('BTC__USD')

        if (REQ_CURRENCY_CODE == 'USD'):
            # Do the conversion to BTC
            BTC_TOTAL = round(Decimal(REQ_PRICE) / Decimal(BTC_USD), 8)

        if (REQ_CURRENCY_CODE == 'CAD'):
            CAD_USD = Decimal(r.get('CAD__USD'))
            USD_TOTAL = Decimal(REQ_PRICE) * CAD_USD # NOW it's in USD
            BTC_TOTAL = round(Decimal(REQ_PRICE) / Decimal(BTC_USD), 8)

        if (INVOICE_ACCOUNT == '0P'):
            queryset2 = MTConnection.objects.filter(acct_owner_id=request.user.id).order_by('created')
            subscriptions = MTCSerializer(queryset2, many=True).data
            import time, datetime
        
            from datetime import datetime, timedelta
            USD_SUBTOTAL = CAD_SUBTOTAL = 0
            for subscription in subscriptions:
                if (subscription['mt4_currency_code']): # Only fully initialized accounts
                    inv_SID = subscription['connection_id']
                    inv_monthly_profit = Decimal(subscription['profit_'+invoice_year_month])
                    inv_currency_code = subscription['mt4_currency_code']
                    TARGET_DATE = invoice_year_month + "-01" # Convert to CAD and USD using historical data for this month
                    TARGET_DATE = TARGET_DATE.replace("_", "-") # TwelveData conversion
                    if (inv_monthly_profit > 0):
                        if (inv_currency_code == 'Bit' or inv_currency_code == 'MBT'):
                            td_currency_code = 'BTC/USD'
                            try:
                                CAD_USD_TARGET_DATE_PRICE = HistoricalPrice.objects.get(target_date=TARGET_DATE, td_currency_code='CAD/USD').to_USD_value
                                BTC_USD_TARGET_DATE_PRICE = HistoricalPrice.objects.get(target_date=TARGET_DATE, td_currency_code=td_currency_code).to_USD_value
                                USD_MONTHLY_PROFIT = (Decimal(BTC_USD_TARGET_DATE_PRICE) * Decimal(inv_monthly_profit))/1000000
                                CAD_MONTHLY_PROFIT = USD_MONTHLY_PROFIT / CAD_USD_TARGET_DATE_PRICE
                                print(inv_SID, inv_monthly_profit, inv_currency_code, round(USD_MONTHLY_PROFIT,2) , "USD", round(CAD_MONTHLY_PROFIT, 2), "CAD")
                                ii = InvoiceItem(connection_id=inv_SID, currency_code=inv_currency_code, USD_price=round(USD_MONTHLY_PROFIT,2), CAD_price=round(CAD_MONTHLY_PROFIT, 2), BTC_price=inv_monthly_profit, price=inv_monthly_profit, invoice_parent=INVOICE_ENTRY_TS)
                                ii.save()
                                USD_SUBTOTAL = USD_SUBTOTAL + USD_MONTHLY_PROFIT 
                                CAD_SUBTOTAL = CAD_SUBTOTAL + CAD_MONTHLY_PROFIT
                            except:
                                return Response("FX HISTORY DATA INCOMPLETE")

                        if (inv_currency_code == 'SZA'):
                            td_currency_code = 'ETH/USD'
                            try:
                                ETH_USD_TARGET_DATE_PRICE = HistoricalPrice.objects.get(target_date=TARGET_DATE, td_currency_code=td_currency_code).to_USD_value
                                CAD_USD_TARGET_DATE_PRICE = HistoricalPrice.objects.get(target_date=TARGET_DATE, td_currency_code='CAD/USD').to_USD_value
                                USD_MONTHLY_PROFIT = (Decimal(ETH_USD_TARGET_DATE_PRICE) * Decimal(inv_monthly_profit))/1000000
                                CAD_MONTHLY_PROFIT = USD_MONTHLY_PROFIT / CAD_USD_TARGET_DATE_PRICE
                                USD_SUBTOTAL = USD_SUBTOTAL + USD_MONTHLY_PROFIT 
                                CAD_SUBTOTAL = CAD_SUBTOTAL + CAD_MONTHLY_PROFIT
                                print(inv_SID, inv_monthly_profit, inv_currency_code, round(USD_MONTHLY_PROFIT,2) , "USD", round(CAD_MONTHLY_PROFIT, 2), "CAD")
                                ii2 = InvoiceItem(connection_id=inv_SID, currency_code=inv_currency_code, USD_price=round(USD_MONTHLY_PROFIT,2), CAD_price=round(CAD_MONTHLY_PROFIT, 2), price=inv_monthly_profit, invoice_parent=INVOICE_ENTRY_TS)
                                ii2.save()
                            except:
                                return Response("FX HISTORY DATA INCOMPLETE")

                    if (inv_monthly_profit < 0):
                        print("LOSS:", inv_SID, TARGET_DATE, inv_monthly_profit, inv_currency_code)       #if they lose money this month create a notification for admin
                        NEG_FLAG = True

            import redis
            r = redis.Redis(host='domain.com', port=31482, password='hunter2', db=0, decode_responses=True)
            BTC_SUBTOTAL_NOW = USD_SUBTOTAL / Decimal(r.get('BTC__USD'))
            print("REV SHARE |", round(USD_SUBTOTAL, 2), "USD SUBTOTAL", round(CAD_SUBTOTAL,2), "CAD SUBTOTAL", round(BTC_SUBTOTAL_NOW, 5), "BTC SUBTOTAL")
            BTC30 = round(BTC_SUBTOTAL_NOW*Decimal(.3), 5)
            print("USD 30%", round((USD_SUBTOTAL*Decimal(.3)), 2), "CAD 30%", round((CAD_SUBTOTAL*Decimal(.3)),2), "BTC 30%", BTC30)
            BTC_TOTAL = BTC30

        # Void all previous invoices for this user.
        Invoice.objects.filter(invoice_payee_id=request.user.id, is_paid=False).update(is_void=True)
        # Get back the newly created invoice ID and associated data
        tmp = str(self.create(request).data)
        left = tmp[7:]
        import re
        req_all = re.search(r',', left)      # slice until the comma
        req_all_end = int(req_all.start())   # End of closed trades table
        invoice_id = int(left[:req_all_end]) # Trim everything after the table
        BT2 = str(BTC_TOTAL)
        print("PAY", BT2, "BTC |", invoice_id, btc_deposit_address, "+USECREDIT,", round(invoice_credit_used, 8))
        from users.models import User
        user = User.objects.get(pk=request.user.id)
        user.current_invoice_id = invoice_id
        user.BTC_outstanding_balance = BTC_TOTAL
        user.save()
        # Now update this invoice with details
        new_invoice = Invoice.objects.get(pk=invoice_id)
        new_invoice.invoice_total_BTC = BTC_TOTAL
        if (INVOICE_ACCOUNT == '0P'):
            print("rev", invoice_year_month)
            new_invoice.invoice_total_USD = round((USD_SUBTOTAL*Decimal(.3)), 2)
            new_invoice.invoice_total_CAD = round((CAD_SUBTOTAL*Decimal(.3)),2)
            new_invoice.invoice_year_month = invoice_year_month
        new_invoice.invoice_credit_used = invoice_credit_used
        try: # Update the total
            if (invoice_credit_used > 0.00000001):
                BTC_TOTAL = BTC_TOTAL - invoice_credit_used
        except:
            print("invoice credit fail")

        new_invoice.BTC_outstanding_balance = BTC_TOTAL
        new_invoice.btc_deposit_address = btc_deposit_address
        new_invoice.invoice_entry_num = INVOICE_ENTRY_TS
        new_invoice.has_negative_accounts = NEG_FLAG
        new_invoice.save()

        return Response({
            'btc_total': Decimal(BTC_TOTAL),
            'btc_deposit_address': btc_deposit_address
        })

    def put(self, request, pk=None):
        return Response({
            'data': self.partial_update(request, pk).data
        })

    def delete(self, request, pk=None):
        return self.destroy(request, pk)

class InvoiceItemGenericAPIView(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin
):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    pagination_class = CustomPagination

    def get(self, request, pk=None):
        queryset4 = InvoiceItem.objects.all()
        serializer_class = InvoiceItemSerializer(queryset4, many=True)
        queryset4.query = pickle.loads(pickle.dumps(queryset4))
        print(queryset4)
        qs = list(queryset4)
        if pk:
            return Response({
                'data': self.retrieve(request, pk).data
            })

        return self.list(request)

    def post(self, request):
        return Response({
            'data': self.create(request).data
        })

    def put(self, request, pk=None):
        return Response({
            'data': self.partial_update(request, pk).data
        })

    def delete(self, request, pk=None):
        return self.destroy(request, pk)

class NotificationItemGenericAPIView(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin
):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = NotificationItem.objects.all()
    serializer_class = NotificationItemSerializer
    pagination_class = CustomPagination

    def get(self, request, pk=None):
        print("NOTIF", request.user.id)
        queryset6 = NotificationItem.objects.filter(user_id=request.user.id, is_hidden=False).order_by('updated_at')
        notifications = NotificationItemSerializer(queryset6, many=True)

        if pk:
            return Response({
                'data': self.retrieve(request, pk).data
            })

        return Response(notifications.data)

    def post(self, request):
        return Response({
            'data': self.create(request).data
        })

    def put(self, request, pk=None):
        return Response({
            'data': self.partial_update(request, pk).data
        })

    def delete(self, request, pk=None):
        return self.destroy(request, pk)

class WithdrawalItemGenericAPIView(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin
):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = NotificationItem.objects.filter(notification_type=4, processed_on=None)
    serializer_class = NotificationItemSerializer
    pagination_class = CustomPagination

    def get(self, request, pk=None):
        if pk:
            return Response({
                'data': self.retrieve(request, pk).data
            })
        return self.list(request)

    def post(self, request):
        return Response({
            'data': self.create(request).data
        })

    def put(self, request, pk=None):
        return Response({
            'data': self.partial_update(request, pk).data
        })

    def delete(self, request, pk=None):
        return self.destroy(request, pk)

import redis
r = redis.Redis(host='domain.com', port=31482, password='hunter2', db=0, decode_responses=True)

def convert_fx_redis(CURRENCY, VALUE):
    r = redis.Redis(host='domain.com', port=31482, password='hunter2', db=0, decode_responses=True)
    if (CURRENCY == 'Bit' or CURRENCY == 'MBT'):
        return float(r.get('BTC__USD')) / 1000000 * VALUE
    if (CURRENCY == 'SZA'):
        return float(r.get('ETH__USD')) / 1000000 * VALUE
    if (CURRENCY == 'CSH'):
        return float(r.get('BCH__USD')) / 1000000 * VALUE
    if (CURRENCY == 'LTP'):
        return float(r.get('LTC__USD')) / 1000000 * VALUE
    if (CURRENCY == 'AUD'):
        return float(r.get('AUD__USD')) * VALUE
    if (CURRENCY == 'XRP'):
        return float(r.get('XRP__USD')) * VALUE
    if (CURRENCY == 'BRL'):
        return float(r.get('BRL__USD')) * VALUE
    if (CURRENCY == 'GBP'):
        return float(r.get('GBP__USD')) * VALUE
    if (CURRENCY == 'CAD'):
        return float(r.get('CAD__USD')) * VALUE
    if (CURRENCY == 'EUR'):
        return float(r.get('EUR__USD')) * VALUE
    if (CURRENCY == 'CHF'):
        return float(r.get('CHF__USD')) * VALUE
    if (CURRENCY == 'TTH' or CURRENCY == 'USD'): # Tether USD
        return VALUE
    else: return 1

API_URL = 'http://domain.com:8000/api/'


class process1(APIView, ):
    def get(self, request, pk=None):
        import logging
        import ftplib
        import re
        import time, datetime
        from datetime import datetime, timedelta
        import requests
        import os
        from decimal import Decimal
        try:
            import thread
        except ImportError:
            import _thread as thread
        import logging
        import logging.handlers
        import os, time
        
        handler = logging.handlers.WatchedFileHandler(
            os.environ.get("LOGFILE", "1.log"))
        formatter = logging.Formatter(logging.BASIC_FORMAT)
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.setLevel(os.environ.get("LOGLEVEL", "INFO"))
        root.addHandler(handler)
        connection_id = str(pk)
        if pk:
            status = 'PROCESSING'
            tic = time.perf_counter()
            dateTimeObj = datetime.now()
            statement_htm = ""

            if connection_id > '0':
                # Attempt to update the account
                filename = 'statement.htm'
                host = 'domain.com'
                user = 'all'
                passwd = 'hunter2'
                import ftplib
                ftp = ftplib.FTP(host)
                ftp.set_pasv(True)
                ftp.login(user, passwd)
                connection_id = str(connection_id)
                if connection_id in ftp.nlst():
                    ftp.cwd(connection_id)
                    files = []
                    ftp.dir(files.append)
                    if filename in ftp.nlst():
                        localfile = open(filename, 'wb')
                        ftp.retrbinary('RETR ' + filename, localfile.write, 1024)
                        localfile.close()
                        f = open(filename, "r") # Localfile parser workaround
                        for line in f:
                            statement_htm += line
                        f.close()
                    else:
                        print("statement.htm missing!")
                        # Try again in 6 minutes
                        data = {
                            'error': "statement.htm missing!",
                            'status': 6
                        }
                        STAG_URL = 'http://domain.com:7373/'
                        res = requests.get(API_URL + 'retry/' + connection_id) # Retry in 6m
                        return Response(data)
                    # raise Exception(files)            
                else:
                    print('CREATING NEW, NOW SETUP MT4')
                    ftp.mkd(connection_id)
                    ftp.cwd(connection_id)
                    files = []
                    ftp.dir(files.append)
                    print(files)

                ftp.quit() # File downloaded successfully
                tic2 = time.perf_counter()

                # Start processing content
                from bs4 import BeautifulSoup
                statement_soup = BeautifulSoup(statement_htm, 'html.parser')
                TITLE = statement_soup.find('title').get_text()[10:]
                ACCOUNT = statement_soup.find_all('b')[1].get_text()[9:]
                CURRENCY = statement_soup.find_all('td')[2].get_text()[10:]
                LEVERAGE = statement_soup.find_all('td')[3].get_text()[10:]
                date_time_str = statement_soup.find_all('td')[4].get_text()[5:]
                date_time_obj = datetime.strptime(date_time_str, '%B %d, %H:%M')
                datetime_new = date_time_obj + timedelta(minutes=5)
                datetime_new = datetime_new.strftime('%H:%M')
                import pandas as pd
                import numpy as np 
                FLOAT_PNL = statement_soup.find_all('b')[21].get_text()
                FLOAT_PNL = float(FLOAT_PNL.replace(" ", ""))
                DEPOSIT_WITHDRAWAL = statement_soup.find_all('b')[15].get_text()
                DEPOSIT_WITHDRAWAL = float(DEPOSIT_WITHDRAWAL.replace(" ", ""))
                ACCT_FLAGS = ''
                if (DEPOSIT_WITHDRAWAL == 0):
                    DEPOSIT_WITHDRAWAL = 1000
                    ACCT_FLAGS = "D0"
                CLOSED_PNL = statement_soup.find_all('b')[19].get_text()
                try:
                    CLOSED_PNL = float(CLOSED_PNL.replace(" ", ""))
                except Exception as err:
                    pass
                USED_MARGIN = statement_soup.find_all('b')[23].get_text()
                try:
                    USED_MARGIN = float(USED_MARGIN.replace(" ", ""))
                except Exception as err:
                    pass
                BALANCE = statement_soup.find_all('b')[25].get_text()
                BALANCE = float(BALANCE.replace(" ", ""))
                EQUITY = statement_soup.find_all('b')[27].get_text()
                EQUITY = float(EQUITY.replace(" ", ""))
                FREE_MARGIN = statement_soup.find_all('b')[29].get_text()
                FREE_MARGIN = float(FREE_MARGIN.replace(" ", ""))
                mt4_DRAWDOWN_PCT = abs(FLOAT_PNL/BALANCE)*100
                if (USED_MARGIN > 0):
                    FREE_MARGIN_PCT = abs(EQUITY/USED_MARGIN)*100
                else:
                    FREE_MARGIN_PCT = 100
                closed_transactions_html = statement_soup.find_all('table')
                content = statement_soup.find_all('tr', {'align': 'right'})
                if (FLOAT_PNL != 0): # Bot is running
                    closed_trades_html = content[:-8]
                    BOT_RUNNING = True
                else: # No open trades 
                    closed_trades_html = content[:-7]
                    BOT_RUNNING = False

                CLOSED_TRANSACTIONS_COUNT = len(closed_trades_html)
                if CLOSED_TRANSACTIONS_COUNT > 2: # Only process if there is trade history
                    # print("TRANSACTIONS:",CLOSED_TRANSACTIONS_COUNT)
                    closed_trades_head = """<table><thead><tr><td>Ticket</td><td nowrap>Open Time</td><td>Type</td><td>Size</td><td>Item</td><td>Price Closed</td><td>S / L</td><td>T / P</td><td nowrap>Close Time</td><td>Price</td><td>Commission</td><td>Taxes</td><td>Swap</td><td>Profit</td></tr></thead>"""
                    statement_text = "".join(map(str, closed_trades_html))
                    if (BOT_RUNNING):
                        try:
                            closed_trades_html = re.search(r'<b>Closed P/L:</b>', statement_text)
                            closed_trades_idx = int(closed_trades_html.start())  # End of closed trades table
                            clean_closed_trades_html = statement_text[:closed_trades_idx] # Trim everything after the table
                        except:
                            clean_closed_trades_html = statement_text
                    else:
                        clean_closed_trades_html = statement_text
                    try:
                        closed_trades_html = re.search( # Now trim the last row
                            r'<td colspan="10">', clean_closed_trades_html)
                        closed_trades_idx2 = int(closed_trades_html.start())
                        clean_closed_trades_html = statement_text[:closed_trades_idx2 - 19]
                    except:
                        pass
                    res = closed_trades_head + clean_closed_trades_html
                    res += "</table>"
                    df = pd.read_html(res)[0]

                    try:  # remove spaces separating 1000's
                        df['Profit'] = df['Profit'].str.replace(' ', '') 
                        df['Profit']=pd.to_numeric(df.Profit)
                    except: pass
                    try:
                        df['Commission'] = df['Commission'].str.replace(' ', '')
                    except: pass
                    df = df.loc[(df['Type'] != 'balance')]
                    df = df.loc[(df['Type'] != 'credit')]
                    if CLOSED_PNL != 0: # Only process if closed trades
                        FIRST_TRADE_DATE = df.iloc[0]['Open Time']
                        ts_first_trade = datetime.strptime(
                            FIRST_TRADE_DATE, '%Y.%m.%d %H:%M:%S')
                        # print("FIRST TRADE:", ts_first_trade)
                        delta = dateTimeObj - ts_first_trade
                        TRADING_DAYS = np.busday_count(
                            ts_first_trade.date(), dateTimeObj.date())
                        print(f"~Trading days: {TRADING_DAYS} | Total days: {delta.days}")
                        df.rename(columns = {"Close Time": "CloseTimestamp"}, inplace=True)
                        df['CloseTimestamp'] = pd.to_datetime(df.CloseTimestamp, format='%Y.%m.%d %H:%M:%S', )
                        # Convert dataframe format for digest
                        df['Commission'] = pd.to_numeric(df.Commission)
                        df['Taxes'] = pd.to_numeric(df.Taxes)
                        df['Swap'] = pd.to_numeric(df.Swap)
                        df['NetProfit'] = df.apply(lambda row: row.Profit + row.Commission + row.Swap + row.Taxes, axis = 1)
                        df['NetCumProfit'] = np.cumsum(df['NetProfit'])

                        # SORT AFTER TRANSFORMATION
                        df.sort_values(['CloseTimestamp'], ascending=True, inplace = True)
                        PROFIT_MIN = df.min()['Profit']
                        PROFIT_MAX = df.max()['Profit']
                        PROFIT_AVG = df.describe()['Profit']['mean']
                        df.to_csv(connection_id + '.csv', index=True) # CSV verification

                    if (CLOSED_PNL != 0 and DEPOSIT_WITHDRAWAL != 0):
                        try:
                            PROFIT_PCT = (CLOSED_PNL / DEPOSIT_WITHDRAWAL)*100
                        except:
                            PROFIT_PCT = 0
                        if (CLOSED_PNL != 0 and DEPOSIT_WITHDRAWAL != 0):
                            delta_daily = dateTimeObj- timedelta(days=1)
                            string_daily = delta_daily.strftime("%Y.%m.%d")
                            delta_weekly = dateTimeObj - timedelta(days=7)
                            string_weekly = delta_weekly.strftime("%Y.%m.%d")
                            delta_monthly = dateTimeObj - timedelta(days=30.42) # Average Month (365/12) 
                            string_monthly = delta_monthly.strftime("%Y.%m.%d")
                            df_daily = df.loc[(df['CloseTimestamp'] >= string_daily)] 
                            df_weekly = df.loc[(df['CloseTimestamp'] >= string_weekly)] 
                            df_monthly = df.loc[(df['CloseTimestamp'] >= string_monthly)] 
                            PROFIT_DAILY = df_daily['NetProfit'].sum()
                            USD_BALANCE = convert_fx_redis(CURRENCY, BALANCE)
                            USD_CLOSED_PNL = convert_fx_redis(CURRENCY, CLOSED_PNL)
                            PCT_DAILY = (PROFIT_DAILY / BALANCE) * 100
                            USD_DAILY = convert_fx_redis(CURRENCY, PROFIT_DAILY)
                            PROFIT_WEEKLY = df_weekly['NetProfit'].sum()
                            USD_WEEKLY = convert_fx_redis(CURRENCY, PROFIT_WEEKLY)
                            TRADING_WEEKS = TRADING_DAYS / 7
                            PCT_WEEKLY = (PROFIT_WEEKLY / BALANCE) * 100
                            PROFIT_MONTHLY = df_monthly['NetProfit'].sum()
                            USD_MONTHLY = convert_fx_redis(CURRENCY, PROFIT_MONTHLY)
                            TRADING_MONTHS = TRADING_WEEKS / 4
                            PCT_MONTHLY = (PROFIT_MONTHLY / BALANCE) * 100

                            # Calculate monthly profits
                            profit_2020_01 = df.loc[(df['CloseTimestamp'] >= datetime(2020, 1, 1, 0, 0))] 
                            profit_2020_01 = df.loc[(df['CloseTimestamp'] < datetime(2020, 1, 31, 23, 59))] 
                            profit_2020_01 = profit_2020_01['Profit'].sum() + profit_2020_01['Commission'].sum() + profit_2020_01['Swap'].sum()
                            profit_2020_02_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 2, 1, 0, 0))] 
                            profit_2020_02 = profit_2020_02_.loc[(df['CloseTimestamp'] < datetime(2020, 2, 28, 23, 59))] 
                            profit_2020_02 = profit_2020_02['Profit'].sum() + profit_2020_02['Commission'].sum() + profit_2020_02['Swap'].sum()
                            profit_2020_03_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 3, 1, 0, 0))] 
                            profit_2020_03 = profit_2020_03_.loc[(df['CloseTimestamp'] < datetime(2020, 3, 31, 23, 59))] 
                            profit_2020_03 = profit_2020_03['Profit'].sum() + profit_2020_03['Commission'].sum() + profit_2020_03['Swap'].sum()
                            profit_2020_04_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 4, 1, 0, 0))] 
                            profit_2020_04 = profit_2020_04_.loc[(df['CloseTimestamp'] < datetime(2020, 4, 30, 23, 59))] 
                            profit_2020_04 = profit_2020_04['Profit'].sum() + profit_2020_04['Commission'].sum() + profit_2020_04['Swap'].sum()
                            profit_2020_05_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 5, 1, 0, 0))] 
                            profit_2020_05 = profit_2020_05_.loc[(df['CloseTimestamp'] <= datetime(2020, 5, 31, 23, 59))] 
                            profit_2020_05 = profit_2020_05['Profit'].sum() + profit_2020_05['Commission'].sum() + profit_2020_05['Swap'].sum()
                            profit_2020_06_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 6, 1, 0, 0))] 
                            profit_2020_06 = profit_2020_06_.loc[(df['CloseTimestamp'] <= datetime(2020, 6, 30, 23, 59))] 
                            profit_2020_06 = profit_2020_06['Profit'].sum() + profit_2020_06['Commission'].sum() + profit_2020_06['Swap'].sum()
                            profit_2020_07_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 7, 1, 0, 0))] 
                            profit_2020_07 = profit_2020_07_.loc[(df['CloseTimestamp'] <= datetime(2020, 7, 31, 23, 59))] 
                            profit_2020_07 = profit_2020_07['Profit'].sum() + profit_2020_07['Commission'].sum() + profit_2020_07['Swap'].sum()
                            profit_2020_08_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 8, 1, 0, 0))] 
                            profit_2020_08 = profit_2020_08_.loc[(df['CloseTimestamp'] <= datetime(2020, 8, 31, 23, 59))] 
                            profit_2020_08 = profit_2020_08['Profit'].sum() + profit_2020_08['Commission'].sum() + profit_2020_08['Swap'].sum()
                            profit_2020_09_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 9, 1, 0, 0))] 
                            profit_2020_09 = profit_2020_09_.loc[(df['CloseTimestamp'] <= datetime(2020, 9, 30, 23, 59))] 
                            profit_2020_09 = profit_2020_09['Profit'].sum() + profit_2020_09['Commission'].sum() + profit_2020_09['Swap'].sum()
                            profit_2020_10_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 10, 1, 0, 0))] 
                            profit_2020_10 = profit_2020_10_.loc[(df['CloseTimestamp'] <= datetime(2020, 10, 30, 23, 59))] 
                            profit_2020_10 = profit_2020_10['Profit'].sum() + profit_2020_10['Commission'].sum() + profit_2020_10['Swap'].sum()
                            profit_2020_11_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 10, 1, 0, 0))] 
                            profit_2020_11 = profit_2020_11_.loc[(df['CloseTimestamp'] <= datetime(2020, 11, 30, 23, 59))] 
                            profit_2020_11 = profit_2020_11['Profit'].sum() + profit_2020_11['Commission'].sum() + profit_2020_11['Swap'].sum()
                            profit_2020_12_ = df.loc[(df['CloseTimestamp'] >= datetime(2020, 12, 1, 0, 0))] 
                            profit_2020_12 = profit_2020_12_.loc[(df['CloseTimestamp'] <= datetime(2020, 12, 30, 23, 59))] 
                            profit_2020_12 = profit_2020_12['Profit'].sum() + profit_2020_12['Commission'].sum() + profit_2020_12['Swap'].sum()

                            toc2 = time.perf_counter()  # Exclude FTP download time
                            t2 = toc2 - tic2
                            t2 = round(t2, 4)

                            data = {
                                "owner_id": 0,
                                "connection_id": connection_id,
                                "last_modified": dateTimeObj.strftime("%Y-%m-%d"),
                                "first_trade_ts": ts_first_trade.strftime("%Y-%m-%d %H:%M:%S"),
                                "profits_calculated_ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "mt4_title": TITLE,
                                "mt4_free_margin": FREE_MARGIN,
                                "mt4_used_mgn": USED_MARGIN,
                                "mt4_equity": EQUITY,
                                "mt4_FREE_MARGIN_PCT": round(FREE_MARGIN_PCT, 2),
                                "mt4_leverage": LEVERAGE[2:],
                                "mt4_ea_on_off": BOT_RUNNING,
                                "mt4_DRAWDOWN": FLOAT_PNL,
                                "mt4_DRAWDOWN_PCT": round(mt4_DRAWDOWN_PCT, 2),
                                "mt4_CLOSED_PNL": CLOSED_PNL,
                                "mt4_notes": "staging_ETL_1.3 | " + str(t2) + "s",
                                "mt4_last_balance": BALANCE,
                                "acct_flags": ACCT_FLAGS,
                                "mt4_last_balance_usd": round(USD_BALANCE, 2),
                                "mt4_currency_code": CURRENCY,
                                "mt4_deposit": DEPOSIT_WITHDRAWAL,
                                "mt4_tx_count": CLOSED_TRANSACTIONS_COUNT,
                                "mt4_TOTAL_PROFIT_PCT": round(PROFIT_PCT, 2),
                                "mt4_CLOSED_PNL_USD": round(USD_CLOSED_PNL, 2),
                                "mt4_DAILY_PROFIT": round(PROFIT_DAILY, 2),
                                "mt4_DAILY_PROFIT_USD": round(USD_DAILY, 2),
                                "mt4_DAILY_PROFIT_PCT": round(PCT_DAILY, 2),
                                "mt4_WEEKLY_PROFIT": round(PROFIT_WEEKLY, 2),
                                "mt4_WEEKLY_PROFIT_USD": round(USD_WEEKLY, 2),
                                "mt4_WEEKLY_PROFIT_PCT": round(PCT_WEEKLY, 2),
                                "mt4_MONTHLY_PROFIT": round(PROFIT_MONTHLY, 2),
                                "mt4_MONTHLY_PROFIT_USD": round(USD_MONTHLY, 2),
                                "mt4_MONTHLY_PROFIT_PCT": round(PCT_MONTHLY, 2),
                                "profit_2020_01": round(profit_2020_01, 2),
                                "profit_2020_02": round(profit_2020_02, 2),
                                "profit_2020_03": round(profit_2020_03, 2),
                                "profit_2020_04": round(profit_2020_04, 2),
                                "profit_2020_05": round(profit_2020_05, 2),
                                "profit_2020_06": round(profit_2020_06, 2),
                                "profit_2020_07": round(profit_2020_07, 2),
                                "profit_2020_08": round(profit_2020_08, 2),
                                "profit_2020_09": round(profit_2020_09, 2),
                                "profit_2020_10": round(profit_2020_10, 2),
                                "profit_2020_11": round(profit_2020_11, 2),
                                "profit_2020_12": round(profit_2020_12, 2),
                            }
                            # Check if account exists
                            response = requests.get(API_URL + 'get_id/' + connection_id)
                            id = int(response.content.decode('utf8')) # Integer comparison
                            if (id == 0):
                                status = 'INITIALIZED'
                                res = requests.post(API_URL + '_sd', json=data)
                                print(res.content.decode('utf8'))
                                # Create a notification
                                try: # If MTC exists
                                    mtc = MTConnection.objects.get(connection_id=connection_id)
                                    uid = mtc.acct_owner_id
                                    user_id = uid.id
                                except:
                                    user_id = 1 # Admin failsafe
                                    print(connection_id, "does not exist! creating for admin")

                                notif_title = "Account Balace updated " + connection_id
                                notif_details = "You are ready to trade!"
                                n_item = NotificationItem(user_id=user_id, notification_type=5, priority_level=2, notification_title=notif_title, notification_details=notif_details, config_1=connection_id, config_2='', config_3='') 
                                n_item.save() 
                                print("sent notif to", user_id)
                                
                            if (id > 0):
                                status = 'UPDATED'
                                res = requests.put(API_URL + '_sd/' + str(id), json=data)
                                print(res.content.decode('utf8'))

            toc2 = time.perf_counter()
            t3 = toc2 - tic
            print(status ,str(pk), "in",str(t3))
            return Response(str(pk))
            

@api_view(('GET',))
def invoice_details3(request, pk):
    if request.method == 'GET':
        if pk:
            from django.forms.models import model_to_dict
            invoice = Invoice.objects.get(id=pk)
            serializer_class = InvoiceItemSerializer(invoice, many=True)
            invoice.query = pickle.loads(pickle.dumps(invoice))
            IEM = invoice.invoice_entry_num
            if (IEM > 0):
                II = InvoiceItem.objects.filter(invoice_parent=IEM)
                qs = list(II)
                oi_dict = model_to_dict(qs)
                qs = json.dumps(oi_dict, cls=Encoder)
                print(qs)

                return Response({
                    'data': IEM,
                    'details': qs
                })
    if request.method == 'POST':
        print("posted")

class InvoiceDetailsGenericAPIView(generics.GenericAPIView):
    serializer_class = InvoiceItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        invoice_id = self.request.GET.getlist('invoice_id', None)
        print(invoice_id)
        return InvoiceItem.objects.all()

    def get(self, request, pk=None):
        queryset7 = Invoice.objects.get(invoice_payee_id=request.user.id, is_void=False, invoice_entry_num__gt=0)
        invoice_parent_id = queryset7.invoice_entry_num
        pk = invoice_parent_id
        if pk:
            queryset8 = InvoiceItem.objects.filter(invoice_parent=pk)
            invoice_items = InvoiceItemSerializer(queryset8, many=True)
            print(invoice_items.data)
            return Response(invoice_items.data)
        return Response(invoice_items.data)

class AllNotificationItemsGenericAPIView(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin
):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = NotificationItem.objects.all()
    serializer_class = NotificationItemSerializer
    pagination_class = CustomPagination

    def get(self, request, pk=None):
        queryset6 = NotificationItem.objects.filter(user_id=request.user.id).order_by('updated_at')
        notifications = NotificationItemSerializer(queryset6, many=True)
        if pk:
            return Response({
                'data': self.retrieve(request, pk).data
            })

        return Response(notifications.data)
