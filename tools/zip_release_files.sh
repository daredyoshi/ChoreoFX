#!/usr/bin/env bash


if ! command -v 7z &> /dev/null
then
    echo "7z comman not found - is 7zip installed?"
    exit
fi


if [ -z "$1" ]; then
    echo "No valid release version given. Did you update the RELEASE_NOTES?"
    exit 2;
fi

zip_name="ChoreoFX_$1"
dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

folder_2_zip="$dir/$zip_name/"

echo "Moving temp files to $folder_2_zip"


mkdir "$folder_2_zip"
mkdir "$folder_2_zip/ChoreoFX"

cp "$dir/../houdini/"* "$folder_2_zip/ChoreoFX" -r
cp "$dir/../packages" $folder_2_zip -r
cp "$dir/../CONTRIBUTING.md" "$folder_2_zip/ChoreoFX/CONTRIBUTING.md"
cp "$dir/../RELEASE_NOTES.md" "$folder_2_zip/ChoreoFX/RELEASE_NOTES.md"
cp "$dir/../CREDITS.md" "$folder_2_zip/ChoreoFX/README.md"
cp "$dir/../CREDITS.md" "$folder_2_zip/ChoreoFX/CREDIT.md"

echo "Adding files to $zip_name.tar from $folder_2_zip"
tar -zcvf ../$zip_name.tar -C $folder_2_zip $(ls $folder_2_zip)


rm -r $folder_2_zip
