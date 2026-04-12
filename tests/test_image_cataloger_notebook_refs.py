from pathlib import Path

from repo_analyzer.image_cataloger import ImageCataloger


def test_notebook_image_references_are_cataloged(tmp_path: Path):
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "source": [
                    "# Results\n",
                    "![Training Loss](figures/loss_curve.png)\n",
                ],
            },
            {
                "cell_type": "code",
                "source": [
                    "plot_path = 'plots/confusion_matrix.png'\n",
                    "print(plot_path)\n",
                ],
            },
        ]
    }

    nb_path = tmp_path / "analysis.ipynb"
    nb_path.write_text(__import__("json").dumps(notebook), encoding="utf-8")

    output_dir = tmp_path / "out_images"
    cataloger = ImageCataloger()
    entries = cataloger.catalog_images(
        repo_path=tmp_path,
        source_files=[nb_path],
        output_images_dir=output_dir,
    )

    paths = {str(e.get("relative_path")) for e in entries}
    assert "figures/loss_curve.png" in paths
    assert "plots/confusion_matrix.png" in paths

    notebook_entries = [e for e in entries if e.get("source") == "notebook_reference"]
    assert len(notebook_entries) >= 2

    training_entry = next(e for e in notebook_entries if e.get("relative_path") == "figures/loss_curve.png")
    assert "Notebook annotation" in str(training_entry.get("description", ""))

    manifest = output_dir / "image_manifest.json"
    assert manifest.exists()
