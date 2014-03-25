#!/bin/sh
set -e

SNF_MANAGE=$(which snf-manage) ||
    { echo "Cannot find snf-manage in $PATH" 1>&2; exit 1; }

runTest () {
    if [ "$1" = "" ]; then return; fi
    TEST="$SNF_MANAGE test $* --traceback --noinput --settings=synnefo.settings.test"

    runCoverage "$TEST"
}

runCoverage () {
    if [ "$1" = "" ]; then return; fi
    # Stop here, if we are on dry run
    if [ $DRY_RUN ]; then
        echo $1
        return
    fi

    if coverage >/dev/null 2>&1; then
      coverage run $1
      coverage report --include=snf-*
    else
      echo "WARNING: Cannot find coverage in path, skipping coverage tests" 1>&2
      $1
    fi
}

usage(){
    echo "$1: Wrong input."
    echo "    Usage: $0 [--dry-run] component[.app]"
    exit
}

# Append a string to a given variable.
#
# Arguments: $1: the variable name
#            $2: the string
# Note, the variable must be passed by name, so we need to resort to a bit
# compilcated parameter expansions
append () {
    eval $(echo "$1=\"\$${1}\"\" \"\"$2\"")
}

# Check if a string contains a substring
#
# Arguments: $1: The string
#            $2: The substring
# Note, we need to return a truth value to an if statement, so we must echo it.
contains () {
    case "$1" in
        *$2*) return 0;;  # True
        *) return 1;;     # False
    esac
}

# Get a list of apps for a given component. If the given argument is an app,
# then return just it.
#
# Arguments: $1: component to extract apps from
# Returns:   $(astakos/cyclades/pithos/ac)_test_apps,
#            a list with apps to be tested for each component
extract_apps () {
    # Check all components:
        # If the given component matches one of the components:
            # If total match, add the apps of the component to the apps to be
            # tested.
            # Else, if its form matches "component.app", append only the app
            # part
            # Anything else is considered wrong input

    for c in $ALL_COMPONENTS; do
        if [ $(contains $1 $c; echo $?) ]; then
            if [ "$1" = "$c" ]; then
                append "${c}_test_apps" "$(eval "echo \$"${c}"_apps")"
                return
            elif [ $(contains $1 "$c."; echo $?) ]; then
                append "${c}_test_apps" $(echo $1 | sed -e 's/[a-z]*\.//g')
                return
            fi
        fi
    done

    usage $1
}

export SYNNEFO_SETTINGS_DIR=/tmp/snf-test-settings

astakos_apps="im quotaholder_app oa2 logic"
cyclades_apps="api db logic plankton quotas vmapi helpdesk userdata"
pithos_apps="api"
astakosclient_apps="nosetests astakosclient"
ALL_COMPONENTS="astakos cyclades pithos astakosclient"

astakos_test_apps=""
cyclades_test_apps=""
pithos_test_apps=""
astakosclient_test_apps=""

if [ $1 = "--dry-run" ]; then
    DRY_RUN=0
    shift
elif [ $(contains $1 "-"; echo $?) ]; then
    usage $1
fi

TEST_COMPONENTS="$@"
if [ -z "$TEST_COMPONENTS" ]; then
    TEST_COMPONENTS=$ALL_COMPONENTS
fi

# Extract apps from a component
for component in $TEST_COMPONENTS; do
    extract_apps $component
done

echo "-------------------------------------------"
echo "Components to be tested:"
echo "Astakos:       $astakos_test_apps"
echo "Cyclades:      $cyclades_test_apps"
echo "Pithos:        $pithos_test_apps"
echo "Astakosclient: $astakosclient_test_apps"
echo "-------------------------------------------"
echo ""

# For each component, run the necessary tests.
# Note that each component needs different setup, which is handled below

export SYNNEFO_EXCLUDE_PACKAGES="snf-cyclades-app"
runTest $astakos_test_apps

export SYNNEFO_EXCLUDE_PACKAGES="snf-pithos-app"
runTest $cyclades_test_apps

export SYNNEFO_EXCLUDE_PACKAGES="snf-cyclades-app"
runTest $pithos_test_apps

runCoverage $astakosclient_test_apps
