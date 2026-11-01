#!/usr/bin/env bash
# Download every input the study uses into DATA (default: ./data, git-ignored).
# Total download is about 700 MB, almost all of it Voteview member votes.
set -euo pipefail
DATA="${1:-$(dirname "$0")/data}"
mkdir -p "$DATA"/{raw_vv,raw_mp,raw_mkt,raw_leg,raw_dbl}

get() { echo "-> $2"; curl -fsSL --retry 3 -o "$2" "$1"; }

# Voteview party means (DW-NOMINATE), mirror of voteview.com HSall_parties.csv
get https://raw.githubusercontent.com/mohammad98sh/music-genres-visualization/main/data/sources/HSall_parties.csv "$DATA/raw_vv/HSall_parties.csv"

# Manifesto Project MPDS2024a (official copy needs a free account at manifesto-project.wzb.eu)
get https://media.githubusercontent.com/media/LudBandeira/SoDA501/main/MPDataset_MPDS2024a.csv "$DATA/raw_mp/mpds2024a.csv"

# Shiller monthly S&P 500 / dividends / CPI / long rate, and Cboe VIX daily
get https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv "$DATA/raw_mkt/shiller.csv"
get https://raw.githubusercontent.com/datasets/finance-vix/main/data/vix-daily.csv "$DATA/raw_mkt/vix.csv"

# Voteview members and member votes (for party-unity and bipartisan vote shares)
for f in HSall_members.csv HSall_votes.csv; do
  get "https://media.githubusercontent.com/media/clarkep/votes-in-congress/master/raw/$f" "$DATA/raw_leg/$f"
done

# Libgober (2024) comprehensive database of U.S. federal laws
if [ ! -d "$DATA/raw_dbl/repo" ]; then
  git clone -q --depth 1 --filter=blob:limit=5m https://github.com/libgober/database_of_laws.git "$DATA/raw_dbl/repo"
fi
echo "Done: $DATA"
