require 'rake/clean'

entries = ['src/coffee/pin.coffee']
file 'static/js/report.js' => entries do |t|
  sh "cli.js --outfile #{t.name} #{entries.join ' '}"
end

generated = ['static/js/report.js']

CLEAN.include generated

task :default => generated
