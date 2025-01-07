#!/bin/sh
# script to build the resume in .html and .pdf.
# pandoc & wkhtmltopdf are required.

echo
echo 'Convert Markdown to Resume HTML ...'
pandoc -s -c css/design-resume.css README.md -o resume.html
echo 'Done'

echo
echo 'Convert Markdown to temp Resume HTML ...'
pandoc -s -c css/design.css README.md -o resume_2_pdf.html
echo 'Done'

echo
echo 'Convert temp Resume HTML to PDF ...'
wkhtmltopdf --enable-local-file-access --encoding "UTF-8" resume_2_pdf.html resume.pdf

echo
echo 'Removing temp Resume HTML'
rm ./resume_2_pdf.html

echo
echo 'Convert Markdown to HTML Light + Footer (Download Link) ...'
pandoc -s -c css/design-light.css README.md src/footer.md -o index.html
echo 'Done'

echo
echo 'Convert Markdown to HTML Dark + Footer (Download Link) ...'
pandoc -s -c css/design-dark.css README.md src/footer.md -o dark.html
echo 'Done'

echo
echo 'Finish !'