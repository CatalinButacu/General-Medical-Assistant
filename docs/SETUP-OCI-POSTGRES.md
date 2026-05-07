# Provision PostgreSQL on Oracle Cloud (Always Free, via Terraform)

End state: a Postgres 16 server running on a free OCI ARM Ampere VM with the
schema applied, reachable on port 5432, and a `DATABASE_URL` ready to paste
into the HuggingFace Space.

Total CLI work: ~5 min after the one-time UI prep below. Manual click-through
fallback is at the bottom if you prefer to skip Terraform.

---

## Prerequisites

- OCI account, signed up + verified ([signup.oraclecloud.com](https://signup.oraclecloud.com/)). Pick **Always Free** tier.
- Region locked to a single region — Frankfurt (eu-frankfurt-1) recommended for EU.
- [Terraform CLI](https://developer.hashicorp.com/terraform/install) installed locally (`terraform -version` should print 1.5+).
- An SSH keypair you can paste the public half of. If you don't have one: `ssh-keygen -t ed25519 -C "you@example.com"`.

## Step 1 — Generate an OCI API key (one-time UI work, ~3 min)

Terraform talks to OCI via an API key tied to your user.

1. OCI Console → top-right user icon → **My profile**
2. Resources sidebar → **API keys**
3. **Add API key → Generate API key pair**
4. Click **Download Private Key** ⚠️ you cannot recreate this later
5. Save it as `~/.oci/oci_api_key.pem` (or wherever you want — note the path)
6. Click **Add**
7. **Configuration File Preview** modal pops up. Copy the contents — you need:
   - `tenancy=ocid1.tenancy.oc1...`
   - `user=ocid1.user.oc1...`
   - `fingerprint=ab:cd:ef:...`

Optional but recommended: `chmod 600 ~/.oci/oci_api_key.pem`.

## Step 2 — Configure Terraform variables (~2 min)

```bash
cd infra/oci
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars
```

Fill in the values from Step 1 plus your SSH public key. The tfvars file is
gitignored — never commit it.

## Step 3 — Apply (~3 min provisioning)

```bash
terraform init
terraform plan      # sanity check — review the resources Terraform will create
terraform apply     # type 'yes' when prompted
```

If you see **`Out of host capacity` for the Ampere shape** (common — Always Free
A1 capacity rotates between Availability Domains):

```bash
# Try a different AD: edit terraform.tfvars
availability_domain_index = 1    # was 0; try 1 or 2

terraform apply
```

If still failing after rotating all 3 ADs, wait 15–30 min and retry. OCI rate-limits
Ampere creation; capacity opens regularly. Last resort: use `VM.Standard.E2.1.Micro`
(also always-free, AMD, 1 GB RAM — tight but workable).

## Step 4 — Wait for cloud-init to finish (~3 min after VM is Running)

Terraform returns the moment the VM is allocated. Postgres install happens after,
inside the VM via cloud-init.

Watch progress:

```bash
ssh ubuntu@$(terraform output -raw public_ip) 'sudo tail -f /var/log/medassist-init.log'
```

Wait for `touch /var/lib/medassist-bootstrap-complete` (last line). Then exit ssh.

## Step 5 — Capture the connection string

```bash
terraform output -raw database_url
```

Outputs something like:
```
postgresql://medassist:gA9X...@193.122.x.x:5432/medassist?sslmode=require
```

## Step 6 — Smoke-test

```bash
psql "$(terraform output -raw database_url)" -c '\dt'
```

Should list `health_profiles` and `cabinet_items`. If yes — Postgres is live and
ready to receive traffic from the FastAPI backend.

## Step 7 — Wire it into the HuggingFace Space

[https://huggingface.co/spaces/catalinbutacu/med-assist/settings](https://huggingface.co/spaces/catalinbutacu/med-assist/settings)
→ **Variables and secrets → New secret** for each:

| Name | Value |
|---|---|
| `DATABASE_URL` | output from Step 5 |
| `AUTH0_DOMAIN` | same as your `VITE_AUTH0_DOMAIN` (e.g. `dev-xxx.eu.auth0.com`) |
| `AUTH0_AUDIENCE` | from Step 8 below |

The HF Space auto-restarts when secrets change.

## Step 8 — Configure Auth0 to issue access tokens (~3 min)

The frontend will request access tokens with a specific audience; the backend
verifies that audience.

1. [Auth0 dashboard](https://manage.auth0.com) → **Applications → APIs → Create API**
2. Name: `Med Assist API`
3. Identifier: `https://med-assist-api` (any URL — doesn't have to resolve)
4. Signing algorithm: **RS256**
5. Save

GitHub repo secret (frontend uses this at build time):

| Name | Value |
|---|---|
| `VITE_AUTH0_AUDIENCE` | `https://med-assist-api` (same identifier) |

## Step 9 — Verify end-to-end

After the HF Space restarts:

```bash
# Anonymous request — should return 401, NOT 500
curl -i https://catalinbutacu-med-assist.hf.space/user/profile
```

`401 Unauthorized` is the success state — it means the route is wired and JWT
validation is rejecting unauthenticated traffic. The frontend migration (next
phase) will then send valid tokens and get real data back.

---

## Tear down (when you're done with the project)

```bash
cd infra/oci
terraform destroy
```

Removes the VM, VCN, security list, internet gateway — all the resources Terraform
created. Doesn't touch your OCI account or API keys.

## Hardening checklist (for after it works)

- [ ] Restrict `ingress_cidr_postgres` and `ingress_cidr_ssh` from `0.0.0.0/0` → your home/office IP. Edit `terraform.tfvars`, re-apply.
- [ ] Schedule `pg_dump` backups to OCI Object Storage (also free tier).
- [ ] Disable Postgres `host` (non-SSL) auth — already disabled by our pg_hba.conf, but double-check.
- [ ] Enable `fail2ban` on the VM for SSH brute-force protection.
- [ ] Move Terraform state to remote backend (OCI Object Storage or Terraform Cloud) so multiple machines can manage the same infra.

---

## Manual fallback (skip Terraform, click through UI)

If Terraform isn't an option, the manual steps are: provision VM via OCI Console
(Ampere A1, Ubuntu 22.04, 1 OCPU/6 GB), open port 5432 in the security list,
SSH in, install Postgres 16 from PGDG, create user+db with `psql`, edit
`postgresql.conf` and `pg_hba.conf`, open `ufw` and `iptables`, apply
`db/schema.sql`. Same end state as `terraform apply`, just 30 min of manual work
instead of 5.
