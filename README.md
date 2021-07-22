# Boris's Python MT4 Tools

This is a cherry picked collection of Python scripts I created for building my own Metatrader 4/5 -> Django REST API (automated/scheduled processing `statement.htm` from the MT4 FTP dump) using **Pandas, Numpy, Postgres, Redis, Celery, Prometheus, Docker, Bokeh, and Docker Compose**.

Period: 2020-03~2020-11

## File Descriptions and Purpose

| File Name | Description |
| ----------- | ----------- |
| `views_mt4.py` | Django views for ETL (class `process1`) and fault tolerant asynchronous payment processing using BeautifulSoup4, Pandas, Numpy, Block.io, secondary REST API, pyqrcode, Redis + TwelveData API |
| `views_csv_chart.py` | Using raw SQL statement JOIN fetching PostgreSQL data for Bokeh graphing over JWT-secured REST API |
| `models_mt4_histprice_invoice_notif.py` | Django Models for PostgreSQL for MT4 derived analytics, historical prices, multi currency invoices, and notifications |
| `models_users_roles.py` | Django User models and login handler for logging User Agent/IP upon successful login, assigning role permissions, mapping invoices to users, and handling referral credits |
| /docker | Folder containing Docker configurations for auto renewing TLS 1.3 SSL with certbot, Nginx proxy, and static files for both dev/prod environments  |
| `docker-compose.yml` | Production Docker-Compose v2 config with Certbot running on HTTPS through port 443 |
| `init-letsencrypt.yml` | Automated RSA 4096-bit key generation with staging/production configs and certificate management with auto renewal  |
| `websockets_redis.py` | Use Block.io websockets to watch for BTC blockchain activity on address specified by argument and write JSON response to HA Redis cluster |

## Installing Environment/Requirements

[Docker on Ubuntu 20.04](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04)

```bash
sudo apt install apt-transport-https ca-certificates curl software-properties-common -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
sudo apt update && sudo apt install docker-ce -y
sudo curl -L "https://github.com/docker/compose/releases/download/1.28.6/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### Installing NVM

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
nvm install 16.4.1
nvm use 16.4.1
```
