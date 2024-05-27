# script to build the resume in .html and .pdf.
# pandoc.exe & wkhtmltopdf are required.

Write-Host 'Generate Markdown to HTML ...'
C:\Program` Files\Pandoc\pandoc.exe -s -c css/design.css README.md -o index.html
Write-Host 'Done'

Write-Host
Write-Host 'Generate HTML to PDF ...'
C:\Program` Files\wkhtmltopdf\bin\wkhtmltopdf.exe --enable-local-file-access index.html resume.pdf


Write-Host
Write-Host 'Generate Markdown to HTML Light + Footer (Download Link) ...'
C:\Program` Files\Pandoc\pandoc.exe -s -c css/design-light.css README.md src/footer.md -o index.html
Write-Host 'Done'

Write-Host
Write-Host 'Generate Markdown to HTML Dark + Footer (Download Link) ...'
C:\Program` Files\Pandoc\pandoc.exe -s -c css/design-dark.css README.md src/footer.md -o dark.html
Write-Host 'Done'

Write-Host
Write-Host 'Finish !'