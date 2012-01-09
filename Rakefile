require 'rake/clean'

entries = ['src/coffee/cache-check.coffee']
file 'static/js/page.js' => entries do |t|
  sh "cli.js --outfile #{t.name} #{entries.join ' '}"
end

generated = ['static/js/page.js']

CLEAN.include generated

task :default => generated
