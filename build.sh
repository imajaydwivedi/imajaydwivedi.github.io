#!/bin/sh
# script to build the resume in .html and .pdf.
# pandoc & wkhtmltopdf are required.

echo
echo 'Generate Markdown to HTML ...'
pandoc -s -c css/design.css README.md -o index.html
echo 'Done'

echo
echo 'Generate HTML to PDF ...'
wkhtmltopdf --enable-local-file-access index.html resume.pdf

echo
echo 'Generate Markdown to HTML Light + Footer (Download Link) ...'
pandoc -s -c css/design-light.css README.md src/footer.md -o index.html
echo 'Done'

echo
echo 'Generate Markdown to HTML Dark + Footer (Download Link) ...'
pandoc -s -c css/design-dark.css README.md src/footer.md -o dark.html
echo 'Done'

echo
echo 'Finish !'