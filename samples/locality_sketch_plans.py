import pathlib
import requests


BASE_URL = "http://maps.six.nsw.gov.au/SketchPlansWS/rest/getSketchPlans"
REQUEST_TIMEOUT = 30
SURVEY_MARKS = [
    'TS2761',
    'SS2331',
    'BM2331',  # Not found
]
# populate with desired output path
OUTPUT_DIR = pathlib.Path(r'')

def fetch_sketch(mark: str) -> bytes | None:
    """
    Fetch a locality sketch plan PDF for a given mark.

    :return: PDF bytes if found, otherwise None
    """
    response = requests.get(
        BASE_URL,
        params={"surveyMark": mark},
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code == 200 and response.content:
        return response.content

    return None


def save_pdf(content: bytes, filename: pathlib.Path) -> None:
    """
    Save PDF content to disk.
    """
    with open(filename, "wb") as fh:
        fh.write(content)


def main(output_dir: pathlib.Path) -> None:
    """

    :return: None
    """
    total_survey_marks = len(SURVEY_MARKS)
    not_found: list[str] = []

    for idx, mark in enumerate(SURVEY_MARKS, start=1):
        print(
            f"Retrieving sketch {idx}/{total_survey_marks}: {mark}",
            end="\r",
            flush=True,
        )

        pdf_content = fetch_sketch(mark)

        if pdf_content is None:
            not_found.append(mark)
            continue

        save_pdf(pdf_content, output_dir / f"{mark}.pdf")

    # Write failures
    if not_found:
        with open(output_dir / f"LSPs_not_found.txt", "w", encoding="utf-8") as fh:
            fh.write("\n".join(not_found))

    # Summary
    retrieved = total_survey_marks - len(not_found)
    print(f"\n\nRetrieved {retrieved} of {total_survey_marks} sketches")

    if not_found:
        print("    => See LSPs_not_found.txt")


if __name__ == "__main__":
    main(output_dir=OUTPUT_DIR)