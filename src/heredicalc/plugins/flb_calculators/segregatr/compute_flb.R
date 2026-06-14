#!/usr/bin/env Rscript --vanilla
# compute_flb.R — HerediCalc v4 segregatr FLB computation
#
# Arguments (positional):
#   1: pedigree TSV file (individual_id, father_id, mother_id, sex_code,
#                         is_affected, is_proband, genotype, liability_class)
#   2: penetrance TSV file (rows = liability classes, columns = penetrance_nc,
#                           penetrance_het, penetrance_hom)
#   3: allele frequency (numeric)
#
# Output: exactly one JSON object to stdout:
#   {"flb": <value>, "r_session": {"r_version", "platform", "loaded_namespaces"}}
# Diagnostics (if any) go to stderr only.

suppressPackageStartupMessages({
  library(pedtools)
  library(segregatr)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("Usage: compute_flb.R <ped_file> <pen_file> <allele_freq>")
}

ped_file  <- args[1]
pen_file  <- args[2]
freq_val  <- as.numeric(args[3])

# ----- Read pedigree data -----
ped_data <- read.table(
  ped_file,
  header = TRUE,
  sep = "\t",
  stringsAsFactors = FALSE,
  na.strings = "NA"
)

# ----- Create pedtools pedigree -----
x <- pedtools::ped(
  id  = ped_data$individual_id,
  fid = ped_data$father_id,
  mid = ped_data$mother_id,
  sex = ped_data$sex_code
)

# ----- Build genotype vectors (IDs as character strings) -----
ids <- as.character(ped_data$individual_id)
carriers    <- ids[!is.na(ped_data$genotype) & ped_data$genotype == "Het"]
homozygous  <- ids[!is.na(ped_data$genotype) & ped_data$genotype == "Hom"]
noncarriers <- ids[!is.na(ped_data$genotype) & ped_data$genotype == "Neg"]

# ----- Affection status -----
# affection_known=0 means "." in COOL3 (unknown); affection_known=1 means unaff or affected
affected_ids <- ids[ped_data$is_affected == 1]
unknown_ids  <- ids[ped_data$affection_known == 0]

# ----- Proband -----
proband_ids <- ids[ped_data$is_proband == 1]
if (length(proband_ids) != 1) {
  stop(sprintf("Expected exactly one proband, got %d", length(proband_ids)))
}
proband_id <- proband_ids[1]

# ----- Read penetrance table -----
pen_data <- read.table(
  pen_file,
  header = TRUE,
  sep = "\t",
  stringsAsFactors = FALSE
)
penetrances <- as.matrix(
  pen_data[, c("penetrance_nc", "penetrance_het", "penetrance_hom")]
)

# ----- Build liability vector (1-based for R) -----
liability_vec <- ped_data$liability_class + 1L
names(liability_vec) <- ids

# ----- Compute FLB -----
flb_val <- segregatr::FLB(
  x           = x,
  carriers    = carriers,
  homozygous  = homozygous,
  noncarriers = noncarriers,
  freq        = freq_val,
  affected    = affected_ids,
  unknown     = unknown_ids,
  proband     = proband_id,
  penetrances = penetrances,
  liability   = liability_vec
)

# ----- Collect R session provenance (after the FLB call) -----
json_escape <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s
}
json_str <- function(s) sprintf('"%s"', json_escape(s))

ns_names <- sort(loadedNamespaces())
ns_entries <- vapply(
  ns_names,
  function(n) {
    ver <- tryCatch(as.character(packageVersion(n)), error = function(e) "unknown")
    sprintf("%s: %s", json_str(n), json_str(ver))
  },
  character(1)
)
ns_json <- sprintf("{%s}", paste(ns_entries, collapse = ", "))

r_session_json <- sprintf(
  '{"r_version": %s, "platform": %s, "loaded_namespaces": %s}',
  json_str(R.version.string),
  json_str(R.version$platform),
  ns_json
)

# ----- Output JSON (single object on stdout) -----
cat(sprintf('{"flb": %.15g, "r_session": %s}\n', flb_val, r_session_json))
