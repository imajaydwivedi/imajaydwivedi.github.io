#!/bin/sh
# script to build the resume in .html and .pdf.
# pandoc & wkhtmltopdf are required.

echo
echo 'Convert Markdown to Resume HTML ...'
pandoc -s -c css/design-resume.css README.md -o resume.html #2>/dev/null


echo 'Convert Markdown to temp Resume HTML ...'
pandoc -s -c css/design.css README.md -o resume_2_pdf.html #2>/dev/null

echo 'Convert temp Resume HTML to <<Ajay_Kumar_Dwivedi.pdf>> ...'
wkhtmltopdf --enable-local-file-access --encoding "UTF-8" resume_2_pdf.html Ajay_Kumar_Dwivedi.pdf #2>/dev/null

echo 'Removing temp Resume HTML'
rm ./resume_2_pdf.html

echo 'Convert Markdown to HTML Light + Footer (Download Link) ...'
pandoc -s -c css/design-light.css README.md src/footer.md -o index.html #2>/dev/null

echo 'Convert Markdown to HTML Dark + Footer (Download Link) ...'
pandoc -s -c css/design-dark.css README.md src/footer.md -o dark.html #2>/dev/null

echo
echo 'Finish !'

echo '***************************************************'
echo 'IMPORTANT: Open "resume.html" in chome/brave browser, and print it overwriting "Ajay_Kumar_Dwivedi.pdf"'.
echo '***************************************************'
echo