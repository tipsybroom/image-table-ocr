import os
import sys
import shutil
import json

from doctr.io import DocumentFile
from doctr.models import ocr_predictor

import requests
import table_ocr.util
import table_ocr.extract_tables
import table_ocr.extract_cells
import table_ocr.ocr_image
import table_ocr.ocr_to_csv
def download_image_to_tempdir(url, filename=None, tempdir="ocr_temp"):
    if filename is None:
        filename = os.path.basename(url)
    response = requests.get(url, stream=True)
    tempdir = table_ocr.util.make_tempdir(tempdir)
    filepath = os.path.join(tempdir, filename)
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content():
            f.write(chunk)
    return filepath

def copy_image_to_tempdir(url: str, filename=None, tempdir="ocr_temp"):
    if filename is None:
        filename = os.path.basename(url)
    tempdir = table_ocr.util.make_tempdir(tempdir)
    filepath = os.path.join(tempdir, filename)
    shutil.copyfile(url, filepath)
    return filepath

def main(url, is_local_file=False):
    if is_local_file:
        image_filepath = copy_image_to_tempdir(url)
    else:
        image_filepath = download_image_to_tempdir(url)
    # image_tables = table_ocr.extract_tables.main([image_filepath])
    image_tables = table_ocr.ocr_image.main(image_filepath, None)
    return image_tables

    table_ocr.extract_tables.main(image_tables)
    print("Running `{}`".format(f"extract_tables.main([{image_filepath}])."))
    print("Extracted the following tables from the image:")
    print(image_tables)
    for image, tables in image_tables:
        print(f"Processing tables for {image}.")
        for table in tables:
            print(f"Processing table {table}.")
            cells = table_ocr.extract_cells.main(table)
            ocr = [
                table_ocr.ocr_image.main(cell, None)
                for cell in cells
            ]
            print("Extracted {} cells from {}".format(len(ocr), table))
            print("Cells:")
            for c, o in zip(cells[:3], ocr[:3]):
                with open(o) as ocr_file:
                    # Tesseract puts line feeds at end of text.
                    # Stript it out.
                    text = ocr_file.read().strip()
                    print("{}: {}".format(c, text))
            # If we have more than 3 cells (likely), print an ellipses
            # to show that we are truncating output for the demo.
            if len(cells) > 3:
                print("...")
            return table_ocr.ocr_to_csv.text_files_to_csv(ocr)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # csv_output = main(sys.argv[1], True)
        predictor = ocr_predictor(pretrained=True)
        doc = DocumentFile.from_images(sys.argv[1])
        result = predictor(doc)
        # result.show()
        export = result.export()
        # Flatten the export
        page_words = [[word for block in page['blocks'] for line in block['lines'] for word in line['words']] for page
                      in export['pages']]
        page_dims = [page['dimensions'] for page in export['pages']]
        # Get the coords in [xmin, ymin, xmax, ymax]
        words_abs_coords = [
            [[word['value'],
                int(round(word['geometry'][0][0] * dims[1])), int(round(word['geometry'][0][1] * dims[0])),
              int(round(word['geometry'][1][0] * dims[1])), int(round(word['geometry'][1][1] * dims[0]))] for word in
             words]
            for words, dims in zip(page_words, page_dims)
        ]
        print(words_abs_coords)
        # print(result)
        # print(export)
    else:
        csv_output = main(sys.argv[1], False)
    print()
    print("Here is the entire CSV output:")
    print()
    print(csv_output)
