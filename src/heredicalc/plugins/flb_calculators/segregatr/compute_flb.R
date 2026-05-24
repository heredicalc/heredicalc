#!/usr/bin/env Rscript --vanilla
# compute_flb.R — HerediCalc v4 segregatr FLB computation
#
# Arguments (positional):
#   1: pedigree TSV file (individual_id, father_id, mother_id, sex_code,
#                         is_affected, genotype, liability_class)
#   2: penetrance TSV file (rows = liability classes, columns = penetrance_nc,
#                           penetrance_het, penetrance_hom)
#   3: allele frequency (numeric)
#
# Output: JSON to stdout: {"flb": <value>}

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
# sex_code: 1=male, 2=female; founder parents are 0 (pedtools uses 0 for founders)
x <- pedtools::ped(
  id  = ped_data$individual_id,
  fid = ped_data$father_id,
  mid = ped_data$mother_id,
  sex = ped_data$sex_code
)

# ----- Add genotype marker -----
# Alleles: 1 = wildtype, 2 = carrier (variant)
n_members <- nrow(ped_data)
geno_vec <- rep(NA_character_, n_members)
for (i in seq_len(n_members)) {
  g <- ped_data$genotype[i]
  if (!is.na(g) && g == "Het") {
    geno_vec[i] <- "1/2"
  } else if (!is.na(g) && g == "Neg") {
    geno_vec[i] <- "1/1"
  }
  # Unknown genotype: NA (not typed)
}

x <- pedtools::addMarker(
  x,
  geno    = geno_vec,
  alleles = c("1", "2"),
  afreq   = c(1 - freq_val, freq_val)
)

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
# liability_class from Python is 0-based; R expects 1-based
liability_vec <- ped_data$liability_class + 1L
names(liability_vec) <- as.character(ped_data$individual_id)

# ----- Identify affected individuals -----
affected_ids <- ped_data$individual_id[ped_data$is_affected == 1]

# ----- Compute FLB -----
flb_val <- segregatr::FLB(
  x           = x,
  affected    = affected_ids,
  liability   = liability_vec,
  penetrances = penetrances,
  freq        = freq_val
)

# ----- Output JSON -----
cat(sprintf('{"flb": %.15g}\n', flb_val))
