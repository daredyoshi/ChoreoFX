#!/usr/bin/env bash

awk -v ver="$1" '
 /^## Version / { if (p) { exit }; if ($3 == ver) { p=1; next} } p && NF
' ../RELEASE_NOTES.rst