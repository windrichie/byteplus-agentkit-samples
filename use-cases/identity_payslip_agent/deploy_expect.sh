#!/usr/bin/expect -f
# Drive `agentkit deploy` through its interactive clack prompts.
# Answers "Yes" to "Continue without enabling services?" (mem0 is unused by
# this sample) and lets everything else stream through.
set timeout 1800
set cli [lindex $argv 0]
set cfg [lindex $argv 1]
spawn $cli deploy --config-file $cfg
expect {
    "Continue without enabling services?" {
        # clack select: initial highlight is "No"; arrow-down moves to "Yes"
        after 1000
        send "\033\[B"
        after 500
        send "\r"
        exp_continue
    }
    -re {[Yy]es /} {
        # already answered / other selects: accept default with Enter
        after 500
        send "\r"
        exp_continue
    }
    eof
}
catch wait result
exit [lindex $result 3]
