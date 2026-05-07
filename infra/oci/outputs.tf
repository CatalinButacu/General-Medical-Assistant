output "public_ip" {
  description = "Public IP of the Postgres VM"
  value       = oci_core_instance.db.public_ip
}

output "ssh_command" {
  description = "Connect via SSH"
  value       = "ssh ubuntu@${oci_core_instance.db.public_ip}"
}

output "database_url" {
  description = "Postgres connection string. Set this as DATABASE_URL on the HF Space."
  value       = "postgresql://${var.db_user}:${random_password.db.result}@${oci_core_instance.db.public_ip}:5432/${var.db_name}?sslmode=require"
  sensitive   = true
}

output "db_password" {
  description = "Generated Postgres password. Read with: terraform output -raw db_password"
  value       = random_password.db.result
  sensitive   = true
}
