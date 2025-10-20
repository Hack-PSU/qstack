import { useState } from "react";
import { Button, Container, Title, Text, Paper, Stack, Center, TextInput, Group } from "@mantine/core";
import { IconBrandDiscord, IconMail, IconPhone } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import * as auth from "../api/auth";
import { useUserStore } from "../hooks/useUserStore";

export default function ConnectDiscord() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [showPhoneInput, setShowPhoneInput] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");
  
  const [name, email, role, location, zoomlink, discord, phone, getUser] = useUserStore((store) => [
    store.name,
    store.email,
    store.role,
    store.location,
    store.zoomlink,
    store.discord,
    store.phone,
    store.getUser,
  ]);

  const handleConnectDiscord = () => {
    setIsConnecting(true);
    // Redirect to Discord OAuth login
    window.location.href = "/api/auth/discord/login";
  };

  const formatPhoneNumber = (value: string) => {
    // Remove all non-digits
    const phoneDigits = value.replace(/\D/g, '');
    
    // Limit to 10 digits
    const limitedDigits = phoneDigits.slice(0, 10);
    
    // Format as (XXX) XXX-XXXX
    if (limitedDigits.length <= 3) {
      return limitedDigits;
    } else if (limitedDigits.length <= 6) {
      return `(${limitedDigits.slice(0, 3)}) ${limitedDigits.slice(3)}`;
    } else {
      return `(${limitedDigits.slice(0, 3)}) ${limitedDigits.slice(3, 6)}-${limitedDigits.slice(6)}`;
    }
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value);
    setPhoneNumber(formatted);
  };

  const handleUseEmail = async () => {
    const res = await auth.updateUser({
      name: name,
      email: email,
      role: role,
      location: location,
      zoomlink: zoomlink,
      password: "",
      discord: discord,
      phone: phone,
      preferred: "Email"
    });
    
    if (res.ok) {
      notifications.show({
        title: "Success!",
        color: "green",
        message: "Email set as preferred contact method",
      });
      getUser();
    } else {
      notifications.show({
        title: "Error",
        color: "red",
        message: res.message,
      });
    }
  };

  const handleSubmitPhone = async () => {
    // Validate phone number has exactly 10 digits
    const digits = phoneNumber.replace(/\D/g, '');
    if (digits.length !== 10) {
      notifications.show({
        title: "Invalid Phone Number",
        color: "red",
        message: "Please enter a valid 10-digit US phone number",
      });
      return;
    }

    const res = await auth.updateUser({
      name: name,
      email: email,
      role: role,
      location: location,
      zoomlink: zoomlink,
      password: "",
      discord: discord,
      phone: phoneNumber,
      preferred: "Phone"
    });
    
    if (res.ok) {
      notifications.show({
        title: "Success!",
        color: "green",
        message: "Phone number saved as preferred contact method",
      });
      getUser();
    } else {
      notifications.show({
        title: "Error",
        color: "red",
        message: res.message,
      });
    }
  };

  return (
    <Container size="sm" py="6rem">
      <Paper p="xl" shadow="xs" className="bg-neutral-800">
        <Stack gap="xl" align="center">
          <IconBrandDiscord size={64} color="#5865F2" />

          <Title order={2} ta="center">
            Connect Your Discord Account
          </Title>

          <Text ta="center" c="dimmed">
            To use QStack, you need to connect your Discord account.
            This allows mentors and organizers to reach you for help.
          </Text>

          <Center>
            <Button
              leftSection={<IconBrandDiscord size={20} />}
              size="lg"
              color="indigo"
              onClick={handleConnectDiscord}
              loading={isConnecting}
              disabled={isConnecting}
              fullWidth
            >
              Connect Discord
            </Button>
          </Center>

          <Text ta="center" size="xs" c="dimmed">
            You'll be redirected to Discord to authorize QStack
          </Text>

          <Text ta="center" fw={500} mt="md">
            Or choose an alternative contact method:
          </Text>

          <Group grow style={{ width: '100%' }}>
            <Button
              leftSection={<IconMail size={20} />}
              variant="light"
              color="blue"
              onClick={handleUseEmail}
            >
              Use Your Email
            </Button>

            <Button
              leftSection={<IconPhone size={20} />}
              variant="light"
              color="teal"
              onClick={() => setShowPhoneInput(!showPhoneInput)}
            >
              {showPhoneInput ? "Cancel" : "Add Phone Number"}
            </Button>
          </Group>

          {showPhoneInput && (
            <Stack gap="md" style={{ width: '100%' }}>
              <TextInput
                label="Phone Number"
                placeholder="(123) 456-7890"
                value={phoneNumber}
                onChange={handlePhoneChange}
                maxLength={14}
                size="md"
              />
              <Button
                onClick={handleSubmitPhone}
                color="teal"
                disabled={phoneNumber.replace(/\D/g, '').length !== 10}
              >
                Save Phone Number
              </Button>
            </Stack>
          )}
        </Stack>
      </Paper>
    </Container>
  );
}