require 'rake/clean'

entries = ['src/coffee/cache-check.coffee']
file 'static/js/page.js' => entries do |t|
  sh "cli.js --outfile #{t.name} #{entries.join ' '}"
end

entries = ['src/coffee/list_file.coffee']
file 'static/js/list_file.js' => entries do |t|
  sh "cli.js --outfile #{t.name} #{entries.join ' '}"
end

generated = ['static/js/page.js', 'static/js/list_file.js']

CLEAN.include generated

task :default => generated
