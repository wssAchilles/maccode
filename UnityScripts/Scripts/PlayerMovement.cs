using UnityEngine;

public class PlayerMovement : MonoBehaviour
{
    [SerializeField]
    private float moveSpeed = 5f;

    void Update()
    {
        // Logic 1: Get input using GetAxisRaw for instant, crisp response
        float horizontalInput = Input.GetAxisRaw("Horizontal");
        float verticalInput = Input.GetAxisRaw("Vertical");

        // Logic 2: Create direction vector
        Vector2 moveDirection = new Vector2(horizontalInput, verticalInput);

        // Logic 3: Normalize vector to ensure consistent speed in all 8 directions
        moveDirection.Normalize();

        // Logic 4: Calculate final movement with Time.deltaTime for frame-rate independence
        Vector2 movement = moveDirection * moveSpeed * Time.deltaTime;

        // Logic 5: Apply movement using transform.Translate
        transform.Translate(movement);
    }
}
