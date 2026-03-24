variable "project_id" {
  description = "GCP project id"
  type        = string
  default     = "cerberus-9d94f"
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "asia-east2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "container_images" {
  description = "Container image URIs for Cloud Run services"
  type = object({
    frontend = string
    gateway  = string
    strategy = string
  })
  default = {
    frontend = "asia-east2-docker.pkg.dev/cerberus-9d94f/cerberus/frontend:latest"
    gateway  = "asia-east2-docker.pkg.dev/cerberus-9d94f/cerberus/gateway:latest"
    strategy = "asia-east2-docker.pkg.dev/cerberus-9d94f/cerberus/strategy:latest"
  }
}

variable "gurobi_licenseid" {
  description = "Gurobi WLS LICENSEID"
  type        = string
  sensitive   = true
}

variable "gurobi_wlsaccessid" {
  description = "Gurobi WLS ACCESS ID"
  type        = string
  sensitive   = true
}

variable "gurobi_wlssecret" {
  description = "Gurobi WLS SECRET"
  type        = string
  sensitive   = true
}

variable "firebase_project_id" {
  description = "Firebase project id used by frontend"
  type        = string
  default     = "cerberus-9d94f"
}

variable "firebase_web_config" {
  description = "Firebase Web SDK config values for frontend"
  type = object({
    api_key             = string
    auth_domain         = string
    storage_bucket      = string
    messaging_sender_id = string
    app_id              = string
  })
  default = {
    api_key             = ""
    auth_domain         = ""
    storage_bucket      = ""
    messaging_sender_id = ""
    app_id              = ""
  }
}

variable "firebase_enabled" {
  description = "Enable Firebase writes in strategy service"
  type        = bool
  default     = false
}
