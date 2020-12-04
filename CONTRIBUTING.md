# Links

- [Create ticket and branch](#create-ticket-and-branch)
- [Setting up the Dev Environment](#setting-up-the-dev-environment)
- [Creating a new OTL](#creating-a-new-OTL)
- [Deploying](#Deploying)
- [Licensing](LICENSE)

## How to contribute

If you'd like to contribute, start by searching through the [issues](https://github.com/SunriseProductions/ChoreoFX/issues) and [pull requests](https://github.com/SunriseProductions/ChoreoFX/pulls) to see whether someone else has raised a similar idea or question.

If you don't see your idea listed, and you think it fits into the goals of this guide, do one of the following:
* **If your contribution is minor,** such as a typo fix, open a pull request.
* **If your contribution is major,** such as a new guide, start by opening an issue first. That way, other people can weigh in on the discussion before you do any work.

### Pull Requests

PRs to our libraries are always welcome and can be a quick way to get your fix or improvement slated for the next release. In general, PRs should:

- Only fix/add the functionality in question **OR** address wide-spread whitespace/style issues, not both.
- Add unit or integration tests for fixed or changed functionality (if a test suite already exists).
- Address a single concern in the least number of changed lines as possible.
- Include documentation in the repo or on our [docs site](https://auth0.com/docs).
- Be accompanied by a complete Pull Request template (loaded automatically when a PR is created).

For changes that address core functionality or would require breaking changes (e.g. a major release), it's best to open an Issue to discuss your proposal first. This is not required but can save time creating and reviewing changes.

In general, we follow the ["fork-and-pull" Git workflow](https://github.com/susam/gitpr)

1. Fork the repository to your own Github account
2. Clone the project to your machine
3. Create a branch locally along the naming convention we use below
4. Commit changes to the branch
5. Make sure that any otls adhere to the guidelines set below
6. Push changes to your fork
7. Open a PR in our repository and follow the PR template so that we can efficiently review the changes.

# Create ticket and branch
We use a git flow workflow. If you are unfamiliar with this have a look here:
https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow

We want to track all our activity through git hub's projects. Create an issue on one of our projects describing your issues, and then a branch based off the issue name. Push the branch in order to reserve it.
```
# it can be helpful to make a directory for every ticket
cd /dev/repos/tickets
mkdir 34-Set-up-crowd-Git-project
cd 34-Set-up-crowd-Git-project
git clone https://github.com/SunriseProductions/ChoreoFX.git
cd ChoreoFX
# now to create and push the new branch
git checkout -b 34/Set-up-crowd-Git-project
git push origin 34/Set-up-crowd-Git-project
```

# Setting up the Dev Environment
For anything that is not HDK related you can test by setting an environment variable in your shell before launching houdini, or adding the path of ChoreoFX/HOUDINI_PATH to your houdini environment.

```
# cd to your houdini dir
cd /opt/hfs.18.5/
# source the bash env
source houdini_setup_bash
# append this repo's HOUDINI_PATH folder to the HOUDINI_PATH env var
# don't forget to add the :& so that it doesn't replace it instead
export HOUDINI_PATH="/media/dev/ChoreoFX/houdini:&"
# launch houdini
houdinicore
```

# Creating a new OTL
Use the following convention for label, otl-type, and hda library filename:
    
    <formattedname>
    choreofx::<camelcaseotlname>::<version>
    <context>_<camelcaseotlname>.hda
    
    Example:
    Crowd Blend Transforms
    choreofx::crowdBlendTransforms::1
    SOP_crowdBlendTransforms.hda

Unlike SideFX we prefer to give nodes a version 1. Each Operator library has all of the version associated with that node, but we have separate libraries for each node. This makes things easier to track in git.

Under Tools/Context in the Operator Type Properties Window set the 
"Tab Submenu Path" to 

    ChoreoFX
Make sure that all input and outputs are named and colored correctly.

#### Convert the otl to an expended folder structure with hotl 
Assuming that you have your new SOP "My New Tool" in your Houdini user directory this might look like this:
    
    cd HOUDINI_PATH
    hotl -t ChoreoFX/otls/SOP_myNewTool.hda ~/houdini18.5/otls/SOP_myNewTool.hda
    
More info on hotl here: https://www.sidefx.com/docs/houdini/assets/textfiles.html
If at all possible please try to do this with a commercial license.
    
#### Create a help file for the node
Use the tools/otlautohelp/generate_help_file_from_otls.py to auto generate a basic help with entries for all the parms.

#### Create a test module for the node
TBD - We plan on creating tests for all our nodes

#### Finalize the issue
Update release_notes.rst for the NEXT release
```
* Initial git setup CROWD-43
```
 Squash your commits into a few neat entries (optional)
Navigate to github and create a pull request
Annoy people until they give you an approval and then merge to develop
Never merge to master.


# Debugging tips:

In pycharm add the following to your python paths for convenience
```
/opt/hfs18.0/python/include/python2.7
/opt/hfs18.0/houdini/python2.7libs
```


For HDK to attach a debugger to a running session (assumes a single running Houdini session), use:
```
gdb -p `ps -A | grep houdinicore-bin | sed 's/[^0-9 ].*//'` --ex continue
```


# Running the python tests (not yet implemented)

Run all tests (Standard pytest arguments are passed through!)
```
$ ./test/python/run_tests.sh
```

Run all tests that match a keyword
```
$ ./test/python/run_tests.sh -k locomotion
```

Don't capture stdout
```
$ ./test/python/run_tests.sh -s 
```

Drop into the python debugger
```
$ ./test/python/run_tests.sh --pdb
```

# Deploying 

Only repo admins can deploy and make releases. You can follow the steps below on your own fork if you would like to mirror our release procedure.

All tests muss pass in every houdini version before merging to develop.

All new functionality should be tested after the first iteration is approved

We use a gitflow release procedure

#### Get latest develop

    git checkout develop
    git pull origin develop

#### If this is a new minor release ->
	# Create a release branch
	git checkout -b release/0.1
#### else if this is a patch of an existing release
	git checkout release/0.1
	git merge --no-ff develop

Update RELEASE_NOTES. Include any ticket information possible

Run tests in test/run_tests.sh

Add and Commit changes

    git add RELEASE_NOTES.rst
    git commit -m "Updated release notes"

Zip into an archive with script:

./zip_release_files 0.1.0

Copy the resulting script somwhere outside the directory to upload to the release on github later
   
Update Git

```
git checkout master
git pull origin master
git merge --no-ff release/0.1
git tag 0.1.0
git checkout develop
git merge --no-ff release/0.1
git checkout release/0.1
git push origin master
git push origin develop
git push origin release/0.1
git push origin 1.6.0
```

Add/update the zip to the release on github through the interface there
