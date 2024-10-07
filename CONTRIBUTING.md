# Contributing Guidelines

Thank you for your interest in contributing to our project. Whether it's a bug report, new feature, correction, website page, or additional
documentation, we greatly value feedback and contributions from our community.

Please read through this document before submitting any issues or pull requests to ensure we have all the necessary
information to effectively respond to your bug report or contribution.

## Expected Notebook & Website Page Structure

Your contribution should include both a Jupyter notebook and a corresponding markdown file for the website. Here's what you need to do:

1. Create your Jupyter notebook with the required content.
2. Save the notebook in the appropriate folder, e.g., `repo/agent/function_calling/your_notebook.ipynb`.
3. Create a markdown-only version of the notebook for the website. Make the necessary changes listed below. You can use the following command on terminal to export your notebook as a markdown `jupyter nbconvert --to markdown <YOUR-NOTEBOOK-NAME>.ipynb`.
4. Save the markdown file in the docs folder, mirroring the notebook's location, e.g., `repo/docs/agent/function_calling/your_notebook.md`.

Both the notebook and markdown should include the following sections:

1. <h2>Overview</h2>
2. <h2>Context or Details about feature/use case</h2>
3. <h2>Prerequisites</h2>
4. <h2>Setup</h2>
5. <h2>Your code with comments starts here</h2>
6. <h2>Other Considerations or Advanced section or Best Practices</h2>
7. <h2>Next Steps</h2>
8. <h2>Cleanup</h2>

For the markdown file:
- Include call-to-action links like "Open in GitHub"
- Add necessary TAGS
- Use HTML headers (e.g., <h2>) instead of markdown-style headers

## Reporting Bugs/Feature Requests

We welcome you to use the GitHub issue tracker to report bugs or suggest features.

When filing an issue, please check existing open, or recently closed, issues to make sure somebody else hasn't already
reported the issue. Please try to include as much information as you can. Details like these are incredibly useful:

* A reproducible test case or series of steps
* The version of our code being used
* Any modifications you've made relevant to the bug
* Anything unusual about your environment or deployment


## Contributing via Pull Requests
Contributions via pull requests are much appreciated. Before sending us a pull request, please ensure that:

1. You are working against the latest source on the *main* branch.
2. You check existing open, and recently merged, pull requests to make sure someone else hasn't addressed the problem already.
3. You open an issue to discuss any significant work - we would hate for your time to be wasted.

To send us a pull request, please:

1. Fork the repository.
2. Modify the source; please focus on the specific change you are contributing. If you also reformat all the code, it will be hard for us to focus on your change.
3. Ensure local tests pass.
4. Commit to your fork using clear commit messages.
5. Send us a pull request, answering any default questions in the pull request interface.
6. Pay attention to any automated CI failures reported in the pull request, and stay involved in the conversation.

GitHub provides additional document on [forking a repository](https://help.github.com/articles/fork-a-repo/) and
[creating a pull request](https://help.github.com/articles/creating-a-pull-request/).


## Finding contributions to work on
Looking at the existing issues is a great way to find something to contribute on. As our projects, by default, use the default GitHub issue labels (enhancement/bug/duplicate/help wanted/invalid/question/wontfix), looking at any 'help wanted' issues is a great place to start.


## Code of Conduct
This project has adopted the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct).
For more information see the [Code of Conduct FAQ](https://aws.github.io/code-of-conduct-faq) or contact
opensource-codeofconduct@amazon.com with any additional questions or comments.


## Security issue notifications
If you discover a potential security issue in this project we ask that you notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public github issue.


## Licensing

See the [LICENSE](LICENSE) file for our project's licensing. We will ask you to confirm the licensing of your contribution.
