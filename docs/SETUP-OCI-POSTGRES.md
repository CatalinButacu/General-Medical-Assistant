# Setting up PostgreSQL on Oracle Cloud Always Free tier

End state: a Postgres 16 server running on a free OCI ARM Ampere VM, reachable
from the internet on port 5432, with one DB and one user the FastAPI backend
connects to via `DATABASE_URL`.

Total time: ~30 minutes including waiting for the VM to provision.

---

## 1. Create an OCI account

1. Sign up at <https://signup.oraclecloud.com/> — pick the **Always Free** tier (requires CC for verification, no charge).
2. Choose your home region. Pick **Frankfurt** (eu-frankfurt-1) or **Amsterdam** for EU residency. Once chosen, it can't change for free-tier resources.
3. Wait for the dashboard to load (a few minutes after signup).

## 2. Provision the Always Free Compute instance

1. OCI Console → hamburger menu → **Compute → Instances → Create instance**.
2. Name: `medassist-db`.
3. **Image and shape**: click **Edit**.
   - Image: **Canonical Ubuntu 22.04** (or 24.04).
   - Shape: **Ampere → VM.Standard.A1.Flex**, set to **1 OCPU, 6 GB memory** (always free).
4. **Networking**: leave defaults — OCI auto-creates a VCN. Public IPv4 address: **Assign a public IPv4 address**.
5. **SSH keys**: paste your public SSH key, or have OCI generate one and download both halves.
6. **Boot volume**: 50 GB is fine (always-free includes 200 GB total across volumes).
7. Click **Create**. Wait ~2 min for state = "Running".

## 3. Open port 5432 in the security list

1. From the instance page → click the **subnet** name → **Security Lists** → click the default one.
2. **Add Ingress Rule**:
   - Source CIDR: `0.0.0.0/0`
   - Protocol: TCP
   - Destination port range: `5432`
   - Description: `postgres`
3. Save.

## 4. SSH in and install Postgres 16

```bash
ssh ubuntu@<public-ip>

# Install Postgres 16 from the PGDG repo
sudo apt-get update
sudo apt-get install -y curl ca-certificates gnupg
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
  https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  | sudo tee /etc/apt/sources.list.d/pgdg.list
sudo apt-get update
sudo apt-get install -y postgresql-16

sudo systemctl enable --now postgresql
```

## 5. Create the database and user

```bash
sudo -u postgres psql <<'SQL'
CREATE USER medassist WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
CREATE DATABASE medassist OWNER medassist;
GRANT ALL PRIVILEGES ON DATABASE medassist TO medassist;
SQL
```

Pick a strong password — **this is the only secret protecting your DB**.

## 6. Allow remote connections

Edit `/etc/postgresql/16/main/postgresql.conf`:

```bash
sudo sed -i "s/^#listen_addresses.*/listen_addresses = '*'/" /etc/postgresql/16/main/postgresql.conf
```

Edit `/etc/postgresql/16/main/pg_hba.conf` — add this line at the end (above any `reject` lines):

```
hostssl medassist medassist 0.0.0.0/0 scram-sha-256
```

Note the `hostssl` — forces SSL only. Don't use plain `host` over the public internet.

## 7. Open the host firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 5432/tcp
sudo ufw --force enable

# Iptables rules from the OCI VM image also need updating:
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5432 -j ACCEPT
sudo netfilter-persistent save
```

Restart Postgres:

```bash
sudo systemctl restart postgresql
```

## 8. Apply the schema

From your laptop:

```bash
PGPASSWORD='CHANGE_ME_STRONG_PASSWORD' psql \
  "postgresql://medassist@<public-ip>:5432/medassist?sslmode=require" \
  -f db/schema.sql
```

## 9. Wire it into the HF Space

Construct your `DATABASE_URL`:

```
postgresql://medassist:CHANGE_ME_STRONG_PASSWORD@<public-ip>:5432/medassist?sslmode=require
```

Set it as a HuggingFace Space secret:

1. <https://huggingface.co/spaces/catalinbutacu/med-assist/settings>
2. **Variables and secrets → New secret**
3. Name: `DATABASE_URL`, value: the URL above.

Also add:
- `AUTH0_DOMAIN` — same as `VITE_AUTH0_DOMAIN` (e.g. `dev-xxx.eu.auth0.com`).
- `AUTH0_AUDIENCE` — your Auth0 API identifier (see step 10).

## 10. Configure Auth0 to issue access tokens for this API

1. Auth0 Dashboard → **APIs → Create API**.
2. Name: `Med Assist API`.
3. Identifier: `https://med-assist-api` (or any URL — doesn't have to resolve).
4. Signing algorithm: **RS256**.
5. Save.

Then add a GitHub repo secret:

- Name: `VITE_AUTH0_AUDIENCE`, value: `https://med-assist-api` (same identifier).

The frontend will request access tokens with this audience; the backend will verify it.

---

## Hardening checklist (do these once you've confirmed it works)

- [ ] Restrict the OCI security list ingress to a narrower CIDR (your home/office IP) instead of `0.0.0.0/0`.
- [ ] Set up automatic Postgres backups (`pg_dump` cron + OCI Object Storage upload — also free tier).
- [ ] Set `password_encryption = scram-sha-256` (default in 16, but verify).
- [ ] Disable Postgres superuser remote login (only `medassist` user, never `postgres`).
- [ ] Enable `fail2ban` for SSH on the VM.
- [ ] Set up Let's Encrypt certs and configure Postgres to use them (so clients can verify the server cert, not just trust it).

For a portfolio demo, the baseline above is sufficient. Production would also need: connection pooling (PgBouncer), monitoring (Prometheus exporter), and the hardening above.
