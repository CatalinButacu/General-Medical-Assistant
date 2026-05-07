variable "tenancy_ocid" {
  description = "OCI tenancy OCID — from API key Configuration File Preview"
  type        = string
}

variable "user_ocid" {
  description = "OCI user OCID — from API key Configuration File Preview"
  type        = string
}

variable "api_key_fingerprint" {
  description = "OCI API key fingerprint — shown next to the key in the console"
  type        = string
}

variable "api_private_key_path" {
  description = "Local filesystem path to the OCI API private key (.pem)"
  type        = string
}

variable "region" {
  description = "OCI region — must match where you signed up"
  type        = string
  default     = "eu-frankfurt-1"
}

variable "compartment_ocid" {
  description = "Compartment OCID — use tenancy_ocid for the root compartment"
  type        = string
}

variable "ssh_public_key" {
  description = "Public SSH key (content of ~/.ssh/id_ed25519.pub or similar)"
  type        = string
}

variable "instance_name" {
  description = "OCI compute instance display name"
  type        = string
  default     = "medassist-db"
}

variable "db_user" {
  description = "Postgres role to create"
  type        = string
  default     = "medassist"
}

variable "db_name" {
  description = "Postgres database to create"
  type        = string
  default     = "medassist"
}

variable "ingress_cidr_postgres" {
  description = "CIDR allowed to reach Postgres (5432). Default open; restrict later for security."
  type        = string
  default     = "0.0.0.0/0"
}

variable "ingress_cidr_ssh" {
  description = "CIDR allowed to SSH (22). Default open; restrict to your IP for tighter security."
  type        = string
  default     = "0.0.0.0/0"
}

variable "availability_domain_index" {
  description = "Which AD to deploy into (0/1/2). Switch if you hit Out-of-capacity on Ampere."
  type        = number
  default     = 0
}
