#!/bin/sh
# script to build the resume in .html and .pdf.
# pandoc & wkhtmltopdf are required.

echo
echo 'Convert Markdown to Resume HTML ...'
pandoc -s -c css/design-resume.css README.md -o resume.html #2>/dev/null


echo 'Convert Resume HTML to <<Ajay_Kumar_Dwivedi.pdf>> using headless Chrome ...'
google-chrome --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$(pwd)/Ajay_Kumar_Dwivedi.pdf" \
  "file://$(pwd)/resume.html" 2>/dev/null

echo 'Convert Markdown to HTML Light + Footer (Download Link) ...'
pandoc -s -c css/design-light.css README.md src/footer.md -o index.html #2>/dev/null

echo 'Convert Markdown to HTML Dark + Footer (Download Link) ...'
pandoc -s -c css/design-dark.css README.md src/footer.md -o dark.html #2>/dev/null

echo
echo 'Finish !'

echo '***************************************************'
echo 'PDF generated via headless Chrome from resume.html'
echo '***************************************************'
echo